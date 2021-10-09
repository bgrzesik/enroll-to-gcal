# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# Bartłomiej Grzesik wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return.   Bartłomiej Grzesik
# ----------------------------------------------------------------------------

import sys
import os
import os.path
import argparse
import pickle
import json
import typing
import sqlite3
import itertools
import functools
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from xml.etree import ElementTree

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

def get_calendar_service(cred_file, pickle_file):
    SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

    creds = None
    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                cred_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(pickle_file, 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)

def get_db_connection():
    conn = sqlite3.connect("events.db")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS events(
        event_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        start timestamp NOT NULL,
        end timestamp NOT NULL
    );
    """)
    conn.commit()

    return conn


@dataclass
class EnrollConfig:
    dest_id: str
    source_file: str
    days: typing.List[typing.Tuple[date, str]]

class Lesson(object):
    def __init__(self, data):
        def extract_date(timestamp):
            return datetime.utcfromtimestamp(float(timestamp) / 1000.0)

        self.id = data['id']

        self.title = data['title']
        self.teacher = data['teacher']
        self.place = data['place']
        self.color = data['color']
        self.week_type = data['weekType']
        self.activity_type = data['activityType']

        self.start = extract_date(data['start'])
        self.end = extract_date(data['end'])
        self.first_occurrence_date = extract_date(data['firstOccurrenceDate'])
        self.last_occurrence_date = extract_date(data['lastOccurrenceDate'])

        self.all_day = data['allDay']
        self.editable = data['editable']
        self.importance = data['importance']
        self.points = data['points']
        self.possible = data['possible']
        self.interactive = data['interactive']
        self.show_points = data['showPoints']
        self.one_off = data['oneOff']
        self.assigned_maxes_ratio = data['assignedMaxesRatio']
        self.total_assigned = data['totalAssigned']

    @property
    def event_title(self):
        activity = self.activity_type
        if self.activity_type == 'W':
            activity = 'Lecture'
        elif self.activity_type == 'L':
            activity = 'Laboratory'
        elif self.activity_type == 'C':
            activity = 'Class'

        return '{} {} ({} - {})'.format(self.title, self.week_type, self.place, activity)

    @property
    def event_desc(self):
        return 'Week type: {}\nTeacher: {}\n{}'.format(self.week_type, self.teacher, self.activity_type)

    @property
    def event_repentance(self, until):
        interval = 1 if len(self.week_type) == 0 else 2
        return 'RRULE:FREQ=WEEKLY;UNTIL={};INTERVAL={}'.format(until, interval)

    def __str__(self):
        return '({}, {} {}, {}, {}, {}, {}, {})'.format(self.title,
                                                    self.week_type,
                                                    self.activity_type,
                                                    self.start,
                                                    self.end,
                                                    self.first_occurrence_date,
                                                    self.last_occurrence_date,
                                                    self.teacher)

    def __repr__(self):
        return '{{\n\tevent={}\n\ttime=({}, {})\n\trepentance={}\n}}' \
            .format(self.event_title, self.start, self.end, self.event_repentance)

    @staticmethod
    def get_schedule(source_file):
        tree = ElementTree.parse(source_file)
        tag = tree.findall('./changes/update[@id="form:j_id_12"]')[0].text
        raw = json.loads(tag)
        events = raw['events']
        lessons = map(lambda e: Lesson(e), events)
        lessons = list(lessons)

        return lessons


def clean_cal(dest_id, service, events, db):
    batch = service.new_batch_http_request()
    def remove_event(event_id):
        print(event_id)

        def callback(_1, _2, exception):
            if exception is not None:
                raise exception

            print(event_id, "Done")
            sql = "DELETE FROM events WHERE event_id=?"
            db.execute(sql, (event_id,))
            db.commit()

        batch.add(events.delete(calendarId=dest_id,
                                eventId=event_id), callback=callback)

    for row in db.execute("SELECT event_id, name, start, end FROM events"):
        print(*row)
        remove_event(row[0])

    print(batch.execute())

def get_week_types(events, cal_id, term_start):
    now = datetime(term_start.year, term_start.month, term_start.day).isoformat() + 'Z'
    week_types_events = events.list(
        calendarId=cal_id,
        timeMin=now,
        maxResults=365).execute()

    types = []
    for event in week_types_events.get('items', []):
        day = datetime.strptime(event["start"]["date"], '%Y-%m-%d').date()
        week = event["summary"]

        if "A" in week and "B" not in week:
            week = "A"
        elif "A" not in week and "B" in week:
            week = "B"
        else:
            raise IndexError(f"Unable to guess week type {event}")

        types.append((day, week))

    return dict(types)

def create_semeter(term_start, term_end):
    date = term_start
    week = 0
    days = dict()

    while date <= term_end:
        if date.weekday() >= 5: # is weekend
            date += timedelta(days=1)
            continue

        # I guess there is a better way to do it
        if date.weekday() == 0:
            week += 1

        days[date] = "A" if week % 2 == 0 else "B"
        date += timedelta(days=1)

    return days

def import_schedule(cfg, events, service, db):
    schedule = Lesson.get_schedule(cfg.source_file)
    weekdays = [[] for _ in range(5)]
    weekdays_a = [[] for _ in range(5)]
    weekdays_b = [[] for _ in range(5)]
    colors = {}

    for lesson in schedule:
        weekday = lesson.start.weekday()
        
        if not lesson.week_type:
            weekdays[weekday].append(lesson)
        elif lesson.week_type == "A":
            weekdays_a[weekday].append(lesson)
        elif lesson.week_type == "B":
            weekdays_b[weekday].append(lesson)
        else:
            raise IndexError(f"Unable to guess week type {event}")

    batch = service.new_batch_http_request()
    for day, ty in days.items():
        print(day, ty)
        weekday = day.weekday()
        if ty == "A":
            lessons = itertools.chain(weekdays[weekday], weekdays_a[weekday])
        else:
            lessons = itertools.chain(weekdays[weekday], weekdays_b[weekday])
    
        for lesson in lessons:
            print(lesson)

            color = colors.get(lesson.color)
            if not color:
                color = len(colors.keys())
                colors[lesson.color] = color

            start = datetime(day.year, day.month, day.day, lesson.start.hour, lesson.start.minute)
            end = datetime(day.year, day.month, day.day, lesson.end.hour, lesson.end.minute)

            event = {
                'summary': lesson.event_title,
                'colorId': color,
                'description': lesson.event_desc,
                # 'recurrence': [lesson.event_repentance],
                'start': {
                    'dateTime': start.isoformat(),
                    'timeZone': 'Europe/Warsaw',
                },
                'end': {
                    'dateTime': end.isoformat(),
                    'timeZone': 'Europe/Warsaw',
                },
            }

            def callback(lesson, start, end, id, res, exception):
                if exception is not None:
                    print(exception)

                sql = "INSERT INTO 'events'('event_id', 'name', 'start', 'end') VALUES (?, ?, ?, ?);"
                db.execute(
                    sql, (res["id"],
                        lesson.event_title,
                        start.isoformat(),
                        end.isoformat())
                )
                db.commit()
                print(lesson.title, lesson.start, lesson.end, "Done")

            batch.add(events.insert(calendarId=cfg.dest_id, body=event), 
                                    callback=functools.partial(callback, lesson, start, end))

    batch.execute()

if __name__ == '__main__':
    def date_parse(s): return datetime.strptime(s, '%Y-%m-%d').date()

    arg_parser = argparse.ArgumentParser(description='Utility to import enroll-me results to Google Calendar')
    arg_parser.add_argument('--dest-cal', type=str, help='Google\'s Calendar destination ID')
    arg_parser.add_argument('--cred-file', type=str, help='Google Keys file',  default='credentials.json')
    arg_parser.add_argument('--pickle-file', type=str, help='Google Keys file',  default='token.pickle')

    import_args = arg_parser.add_argument_group('Import related arguments')
    import_args.add_argument('--source-file', type=str)
    import_args.add_argument('--term-start', type=date_parse, help='University Term start date')
    import_args.add_argument('--term-end', type=date_parse, help='University Term end date')
    import_args.add_argument('--week-type-cal', type=str, help='Calendar ID with week type events')
    import_args.add_argument('--swap-weeks', action='store_true', help='Swap week types')

    cleaner_args = arg_parser.add_argument_group('Event cleaner arguements')
    cleaner_args.add_argument('--clean-cal', action='store_true')

    args = arg_parser.parse_args()

    db = None
    try:
        db = get_db_connection()
        service = get_calendar_service(args.cred_file, args.pickle_file)
        events = service.events()

        if args.dest_cal is None:
            arg_parser.error('missing --dest-cal argument')
            sys.exit(1)

        if args.clean_cal:
            clean_cal(args.dest_cal, service, events, db)
            sys.exit(0)

        if args.source_file is None or not os.path.exists(args.source_file):
            arg_parser.error('missing or incorrect --source-file argument')
            sys.exit(1)

        if args.term_start is None:
            arg_parser.error('missing --term-start argument')
            sys.exit(1)

        if (args.term_start is None) or not ((args.term_end is None) ^ (args.week_type_cal is None)):
            arg_parser.error('use either --term-end or --week-type-cal')
            sys.exit(1)
        
        if args.week_type_cal is None:
            days = create_semeter(args.term_start, args.term_end)
        else:
            days = get_week_types(events, args.week_type_cal, args.term_start)

        if args.swap_weeks:
            days = {day: "A" if ty == "B" else "B" for day, ty in days.items()}

        cfg = EnrollConfig(args.dest_cal, args.source_file, days)

        import_schedule(cfg, events, service, db)
        
    finally:
        if db:
            db.close()

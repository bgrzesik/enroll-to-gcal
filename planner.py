# Created by Bartłomiej Grzesik

import json
from datetime import datetime, timedelta
from xml.etree import ElementTree


class Lesson(object):
    def __init__(self, data):
        def extract_date(timestamp):
            return datetime.utcfromtimestamp(float(timestamp) / 1000.0)

        self.id = data["id"]

        self.title = data["title"]
        self.teacher = data["teacher"]
        self.place = data["place"]
        self.color = data["color"]
        self.week_type = data["weekType"]
        self.activity_type = data["activityType"]

        self.start = extract_date(data["start"])
        self.end = extract_date(data["end"])
        self.first_occurrence_date = extract_date(data["firstOccurrenceDate"])
        self.last_occurrence_date = extract_date(data["lastOccurrenceDate"])

        self.all_day = data["allDay"]
        self.editable = data["editable"]
        self.importance = data["importance"]
        self.points = data["points"]
        self.possible = data["possible"]
        self.interactive = data["interactive"]
        self.show_points = data["showPoints"]
        self.one_off = data["oneOff"]
        self.assigned_maxes_ratio = data["assignedMaxesRatio"]
        self.total_assigned = data["totalAssigned"]

    @property
    def event_title(self):
        activity = self.activity_type
        if self.activity_type == "W":
            activity = "Wykład"
        elif self.activity_type == "L":
            activity = "Laborki"
        elif self.activity_type == "C":
            activity = "Ćwiczenia"

        return "{} {} ({} - {})".format(self.title, self.week_type, self.place, activity)

    @property
    def event_desc(self):
        return "Week type: {}\nTeacher: {}\n{}".format(self.week_type, self.teacher, self.activity_type)

    @property
    def event_repentance(self):
        # day = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"][self.start.weekday()]
        interval = 1 if len(self.week_type) == 0 else 2
        # until = self.last_occurrence_date.strftime("%Y%m%d")
        until = "20210616"

        return "RRULE:FREQ=WEEKLY;UNTIL={};INTERVAL={}".format(until, interval)

    @property
    def event_start(self):
        if self.week_type == "B":
            return self.start + timedelta(weeks=2)
        return self.start + timedelta(weeks=1)

    @property
    def event_end(self):
        if self.week_type == "B":
            return self.end + timedelta(weeks=2)
        return self.end + timedelta(weeks=1)

    def __str__(self):
        return "({}, {} {}, {}, {}, {}, {})".format(self.title,
                                                    self.week_type,
                                                    self.activity_type,
                                                    self.event_start,
                                                    self.event_end,
                                                    self.first_occurrence_date,
                                                    self.last_occurrence_date)

    def __repr__(self):
        return "{{\n\tevent={}\n\ttime=({}, {})\n\trepentance={}\n}}" \
            .format(self.event_title, self.event_start, self.event_end, self.event_repentance)


def get_plan():
    tree = ElementTree.parse("enroll.xml")
    tag = tree.findall("./changes/update[@id='form:j_id_12']")[0].text
    raw = json.loads(tag)
    events = raw["events"]
    lessons = map(lambda e: Lesson(e), events)
    lessons = list(lessons)

    return lessons


if __name__ == "__main__":
    from pprint import pprint
    plan = get_plan()

    for lesson in plan:
        print(lesson)


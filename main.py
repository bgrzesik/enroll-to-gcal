# Created by Bartłomiej Grzesik

from db import get_db_connection
from gcalendar import get_calendar_service, CALENDAR_ID
from planner import get_plan, Lesson

COLORS = {
    "Algebra": 1,
    "Algebra+": 1,
    "Algebra(powtarzający)": 2,
    "Analiza matematyczna 1": 3,
    "Analiza matematyczna 1+": 3,
    "Analiza matematyczna 1 (powtarzający)": 4,
    "Matematyka dyskretna": 5,
    "Matematyka dyskretna+": 5,
    "Matematyka dyskretna(powtarzający)": 6,
    "Kompetencje interpersonalne": 7,
    "Wprowadzenie do systemu UNIX": 8,
    "Wstęp do informatyki": 9,
    "Wstęp do informatyki+": 9,
    "Wstęp do informatyki (powtarzający)": 10,
    "Wychowanie fizyczne": 11,
    "Wychowanie fizyczne - chłopcy": 11,
}

conn = get_db_connection()

service = get_calendar_service()
events = service.events()

batch = service.new_batch_http_request()


def add_event(lesson):
    print(lesson)
    event = {
        'summary': lesson.event_title,
        # 'colorId': lesson.color,
        'colorId': COLORS[lesson.title],
        'description': lesson.event_desc,
        'recurrence': [lesson.event_repentance],
        'start': {
            'dateTime': lesson.event_start.isoformat(),
            'timeZone': 'Europe/Warsaw',
        },
        'end': {
            'dateTime': lesson.event_end.isoformat(),
            'timeZone': 'Europe/Warsaw',
        },
    }

    def callback(id, res, exception):
        print(lesson.title, lesson.event_start, lesson.event_end, "Done")
        sql = "INSERT INTO 'events'('event_id', 'name', 'start', 'end') VALUES (?, ?, ?, ?);"
        conn.execute(
            sql, (res["id"],
                  lesson.event_title,
                  lesson.event_start.isoformat(),
                  lesson.event_end.isoformat())
        )
        conn.commit()

    batch.add(events.insert(calendarId=CALENDAR_ID,
                            body=event), callback=callback)


# add_event("TEST", datetime.today(), datetime.today() + timedelta(hours=1))

plan = get_plan()
for lesson in plan:
    add_event(lesson)

print(batch.execute())
conn.close()

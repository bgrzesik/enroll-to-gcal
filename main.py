# Created by Bartłomiej Grzesik

from db import get_db_connection
from gcalendar import get_calendar_service, CALENDAR_ID
from planner import get_plan, Lesson

colors = {}
conn = get_db_connection()

service = get_calendar_service()
events = service.events()

batch = service.new_batch_http_request()


def add_event(lesson):
    print(lesson)

    color = colors.get(lesson.color)
    if not color:
        color = len(colors.keys())
        colors[lesson.color] = color

    event = {
        'summary': lesson.event_title,
        'colorId': color,
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

# Created by Bartłomiej Grzesik

from db import get_db_connection
from gcalendar import get_calendar_service, CALENDAR_ID

conn = get_db_connection()
service = get_calendar_service()
events = service.events()

batch = service.new_batch_http_request()


def remove_event(event_id):
    print(event_id)

    def callback(_1, _2, exception):
        if exception is not None:
            raise exception

        print(event_id, "Done")
        sql = "DELETE FROM events WHERE event_id=?"
        conn.execute(sql, (event_id,))
        conn.commit()

    batch.add(events.delete(calendarId=CALENDAR_ID,
                            eventId=event_id), callback=callback)


for row in conn.execute("SELECT event_id, name, start, end FROM events"):
    print(*row)
    remove_event(row[0])

print(batch.execute())
conn.close()

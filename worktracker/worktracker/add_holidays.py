import os
import django
from jdatetime import datetime , timedelta , date
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE','worktracker.settings')
django.setup()
from timetracker.models import HolidayDay


dates_str = [
    "1/22", "1/29", "2/4", "2/5", "2/12", "2/19", "2/26", "3/2", "3/9", "3/14", "3/15", "3/16",
    "3/23", "3/24", "3/30", "4/6", "4/13", "4/14", "4/15", "4/20", "4/27", "5/3", "5/10", "5/17",
    "5/23", "5/24", "5/31", "6/2", "6/7", "6/10", "6/14", "6/19", "6/21", "6/28", "7/4", "7/11",
    "7/18", "7/25", "8/2", "8/9", "8/16", "8/23", "8/30", "9/3", "9/7", "9/14", "9/21", "9/28",
    "10/5", "10/12", "10/13", "10/19", "10/26", "10/27", "11/3", "11/10", "11/15", "11/17",
    "11/22", "11/24", "12/1", "12/8", "12/15", "12/20", "12/22", "12/29"
]

year = 1404

HolidayDay.objects.all().delete()

for date_str in dates_str:
    shamsi_date = datetime.strptime(f"{year}/{date_str}", "%Y/%m/%d")
    print(shamsi_date)
    HolidayDay.objects.create(
        day = shamsi_date ,
        is_holiday=True,
        is_friday = False
    )

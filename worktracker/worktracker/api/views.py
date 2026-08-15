from multiprocessing import context
from rest_framework.decorators import api_view  , permission_classes
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from timetracker.models import RecordedApp , RecordedWebsite , SystemConfig , WorkRecord , AppRecord ,RecordInactiveTime , UserError
from .serializers import *
import json
import datetime
import jdatetime



@api_view(('GET',))
@permission_classes([IsAuthenticated])
def initialize_record_variables(request):
    """
        initialize app and website name and config variables for record
    """
    apps = RecordedApp.objects.all()
    app_serializer = AppSerializer(apps, many=True)
    websites = RecordedWebsite.objects.all()
    website_serializer = WebsiteSerializer(websites, many=True)
    system_config = SystemConfig.objects.first()
    context = {'success':True,'user_id':request.user.id,'apps':app_serializer.data,'websites':website_serializer.data,'allowed_inactive_time':system_config.allowed_inactive_time}
    return Response(context)


from django.db import transaction


def update_records_without_end(user,records):
    updated_ids = []

    for record in records:
        start_dt = datetime.datetime.strptime(record['start'], '%Y-%m-%d %H:%M:%S.%f')
        start_dt = jdatetime.datetime.fromgregorian(datetime=start_dt)
        rec_obj = WorkRecord.objects.filter(user=user,start=start_dt)
        if rec_obj.exists() and rec_obj.first().end:
            updated_ids.append(record['id'])

    context = {'success':True,'updated_ids':updated_ids}
    return Response(context)


@api_view(('POST',))
@permission_classes([IsAuthenticated])
@transaction.atomic
def update_records(request):
    records = json.loads(request.data['records'])
    if request.data.get('update_type') == '2':
        return update_records_without_end(request.user,records)
    
    updated_ids = []
    
    for record in records:
        try:
            # start to jdatetime
            start_dt = datetime.datetime.strptime(record['start'], '%Y-%m-%d %H:%M:%S.%f')
            start_dt = jdatetime.datetime.fromgregorian(datetime=start_dt)

            # get record if already created
            rec_obj = WorkRecord.objects.filter(user=request.user,start=start_dt)

            # continue if record already updated 
            if rec_obj.exists() and rec_obj.first().is_updated :
                continue

            if record['end']:
                # end to jdatetime
                end_dt = datetime.datetime.strptime(record['end'], '%Y-%m-%d %H:%M:%S.%f')
                end_dt = jdatetime.datetime.fromgregorian(datetime=end_dt)
            
            if 'last_updated' in record and record['last_updated']:
                # last updated to jdatetime
                last_updated = datetime.datetime.strptime(record['last_updated'], '%Y-%m-%d %H:%M:%S.%f')
                last_updated = jdatetime.datetime.fromgregorian(datetime=last_updated)
            else:
                last_updated = None 

            # record exists and has end
            if rec_obj.exists() and record['end']:
                sum_w = record['string']['sum_words'] if 'sum_words' in  record['string'] else None
                rec_obj.update(
                    end=end_dt,
                    inactive_time=record['string']['sum_inactive_time'],
                    sum_words=sum_w,
                    is_updated=True,
                    last_updated = last_updated
                )
                add_inactive_times_to_record(rec_obj.first(),record['string']['inactive_times'])
                if 'logs' in record['string']:
                    create_record_logs(rec_obj.first(),record['string']['logs'])
                update_app_records(record,rec_obj.first())
                updated_ids.append(record['id'])

            # record not exists and has end
            elif not rec_obj.exists() and record['end']:
                sum_w = record['string']['sum_words'] if 'sum_words' in  record['string'] else None
                rec_obj = WorkRecord.objects.create(
                    user=request.user,
                    start=start_dt,
                    end=end_dt,
                    inactive_time=record['string']['sum_inactive_time'],
                    sum_words=sum_w,
                    is_updated=True,
                    last_updated=last_updated
                )  
                add_inactive_times_to_record(rec_obj,record['string']['inactive_times'])
                if 'logs' in record['string']:
                    create_record_logs(rec_obj,record['string']['logs'])
                update_app_records(record,rec_obj)
                updated_ids.append(record['id'])

            # record not exists and has not end
            elif not rec_obj.exists() and not record['end']:
                sum_w = record['string']['sum_words'] if 'sum_words' in  record['string'] else None
                rec_obj = WorkRecord.objects.create(
                    user=request.user,
                    start=start_dt,
                    sum_words=sum_w,
                    last_updated=last_updated
                )
                add_inactive_times_to_record(rec_obj,record['string']['inactive_times'])
                if 'logs' in record['string']:
                    create_record_logs(rec_obj,record['string']['logs'])
                update_app_records(record,rec_obj)

            # # record exists and has not end
            elif rec_obj.exists() and not record['end']:
                sum_w = record['string']['sum_words'] if 'sum_words' in  record['string'] else None
                rec_obj.update(
                    inactive_time=record['string']['sum_inactive_time'],
                    sum_words=sum_w,
                    last_updated=last_updated
                )
                add_inactive_times_to_record(rec_obj.first(),record['string']['inactive_times'])
                if 'logs' in record['string']:
                    create_record_logs(rec_obj.first(),record['string']['logs'])
                update_app_records(record,rec_obj.first())

        except Exception as e:
            # save errors log
            print(f' update_records error: {e}')
            save_error(request.user,e,str(record))
            return Response({'success':False})

    context = {'success':True,'updated_ids':updated_ids}
    return Response(context)


def save_error(user,e,json_text):
    UserError.objects.get_or_create(
        user = user,
        error_text = str(e),
        json_text = json_text
    )


import re
from urllib.parse import urlparse

def extract_domain(text):
    parsed = urlparse(text if text.startswith("http") else "http://" + text)
    return parsed.netloc

def clean_log(log):
    # Switched domain: فقط دامین رو نگه‌دار
    if "Switched domain:" in log:
        log = re.sub(
            r"(Switched domain:\s*)(.*?→\s*)?([^\|]+)",
            lambda m: f"{m.group(1)}{extract_domain(m.group(3)) or 'others'}",
            log
        )

    # Switched app: فقط اسم اپ مثل Telegram یا Google Chrome بمونه
    if "Switched app:" in log:
        log = re.sub(
            r"(Switched app:\s*)([^→\|\n]+)(\s*→\s*[^|]+)?",
            lambda m: f"{m.group(1)}{m.group(2).strip().split()[0]}",
            log
        )

    return log

def create_record_logs(record, logs):
    record.logs.all().delete()

    for log in logs:
        if "Switched app:" in log:
            continue
        cleaned_log = clean_log(log)
        record.logs.create(text=cleaned_log)

from django.utils import timezone

def add_inactive_times_to_record(record,inactive_times):
    """ 
        add work record inactive times to object
    """
    try:
        # clear record old inactive times
        record.inactive_times.all().delete()

        for item in inactive_times:

            # add work record end to inactive end if inactive have not end
            if not item['end'] and record.end:
                item['end'] = record.end.togregorian().strftime("%Y-%m-%d %H:%M:%S.%f")

            if item['end']:
                # split inactive if start_time and end_time not in same say
                start_dt = datetime.datetime.strptime(item['start'], '%Y-%m-%d %H:%M:%S.%f')
                end_dt = datetime.datetime.strptime(item['end'], '%Y-%m-%d %H:%M:%S.%f')
                if start_dt.day != end_dt.day:
                    split_inactive_time(record,start_dt,end_dt)
                    continue
            
            # inactive time have not end
            RecordInactiveTime.objects.create(
                work_record = record,
                start = item['start'],
                end=item['end']
            )
            
            user_profile = record.user.profile
            
            if record.end:
                start_dt = datetime.datetime.strptime(item['start'], '%Y-%m-%d %H:%M:%S.%f')
                end_dt = datetime.datetime.strptime(item['end'], '%Y-%m-%d %H:%M:%S.%f')

                # Convert record datetimes to naive for comparison
                record_start = record.start
                record_end = record.end
                if timezone.is_aware(record_start):
                    record_start = timezone.make_naive(record_start)
                if timezone.is_aware(record_end):
                    record_end = timezone.make_naive(record_end)

                # Calculate inactive duration
                inactive_duration = end_dt - start_dt
                inactive_mins = inactive_duration.total_seconds() / 60
                
                # specific inactive time split time for users (based on user profile)
                system_config = SystemConfig.objects.first()
                allowed_inactive = system_config.allowed_inactive_time_in_person if user_profile.in_person else system_config.allowed_inactive_time
                if user_profile.inactive_time_delete_min:
                    allowed_inactive =  user_profile.inactive_time_delete_min

                if inactive_mins <= int(allowed_inactive) :
                    continue  # Skip this inactive time
                
                # if inactive record start and end is in work record range
                if start_dt > record_start and end_dt < record_end:
                    # split work record and remove inactive time from it
                    WorkRecord.objects.create(user=record.user, start=end_dt, end=record.end, p_record=record)
                    record.end = start_dt
                    record.save()
                else:
                    # check inactive is in already splited records 
                    for rc in record.sub_records.all():
                        rc_start = rc.start
                        rc_end = rc.end
                        if timezone.is_aware(rc_start):
                            rc_start = timezone.make_naive(rc_start)
                        if timezone.is_aware(rc_end):
                            rc_end = timezone.make_naive(rc_end)
                            
                        # if inactive record start and end is in work sub record
                        if start_dt > rc_start and end_dt < rc_end:
                            # split work sub record and remove inactive time from it
                            WorkRecord.objects.create(user=record.user, start=end_dt, end=rc.end, p_record=record)
                            rc.end = start_dt
                            rc.save()
                            break
    except Exception as e:
        print(f'add inactive times error: {e}')
        

def split_inactive_time(record,start_dt,end_dt):
    """
        Split inactive time when start date and end date is not same
    """

    inactive_1_start = start_dt
    inactive_1_end = tz.localize(datetime(start_dt.year, start_dt.month, start_dt.day,23,59,59))

    inactive_2_start = tz.localize(datetime(end_dt.year, end_dt.month, end_dt.day,0,0,0))
    inactive_2_end = end_dt

    RecordInactiveTime.objects.create(
        work_record = record,
        start = inactive_1_start,
        end= inactive_1_end
    )
    RecordInactiveTime.objects.create(
        work_record = record,
        start = inactive_2_start,
        end = inactive_2_end
    )


def update_app_records(record,rec_obj):
    rec_obj.app_records.all().delete()
    for app_name , sec in record['string']['apps'].items():
        if sec == 0:
            continue
        app_obj = RecordedApp.objects.get(name=app_name)
        app_rec = AppRecord.objects.create(work_record=rec_obj,app=app_obj,w_time=abs(sec))

    for app_name , value in record['string']['browser_apps'].items():
        for site_name , sec in value.items() :
            if sec == 0:
                continue
            app_obj = RecordedApp.objects.get(name=app_name)
            website_obj = RecordedWebsite.objects.get(domain=site_name)
            app_rec = AppRecord.objects.create(work_record=rec_obj,app=app_obj,website=website_obj,w_time=abs(sec))


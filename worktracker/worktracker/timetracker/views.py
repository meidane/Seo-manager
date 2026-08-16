#  from core
import requests
import pytz
import time
import datetime as edatetime

# from django core
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse , HttpResponse , Http404 , HttpResponseRedirect
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction

# from third-party apps
from jdatetime import datetime , timedelta , date

# from this app
from .models import *


# def delete_inactives(): 
#     for record in WorkRecord.objects.all():
#         for item in record.inactive_times.all():
#             if record.end:
#                 print(' record has end')
#                 start_dt = item.start
#                 end_dt = item.end
#                 if start_dt > record.start and end_dt < record.end:
#                     print('item in record between')
#                     WorkRecord.objects.create(user=record.user,start=end_dt,end=record.end,p_record=record)
#                     record.end = start_dt
#                     record.save()
#                 else:
#                     for rc in record.sub_records.all():
#                         print('item in child between')
#                         if start_dt > rc.start and end_dt < rc.end:
#                             WorkRecord.objects.create(user=record.user,start=end_dt,end=rc.end,p_record=record)
#                             rc.end = start_dt
#                             rc.save()
#                             break

@login_required(login_url='login')
def index(request):
    rec = WorkRecord.objects.filter(user = request.user).last()
    if rec and not rec.end:
        unfinished_rec = rec #check_unfinished_record(rec,request.user)
        start_time = unfinished_rec.start.time()
        diff = record_time(unfinished_rec)
        sum_minutes = diff
    user_records = []
    jday = datetime.now()

    
    if not request.user.is_staff:
        # not staff users only seen themselves
        user_objs = User.objects.filter(profile__isnull=False,id=request.user.id)
    else:
        user_objs = User.objects.filter(profile__isnull=False)

    # get users data
    for usr in user_objs:
        item = {
            'id':usr.id,
            'name':usr.first_name + ' ' + usr.last_name ,
            'vocations':[],
            'records':[] ,
            'sum_minutes': 0,
            'sum_inactive':0,
            'weekday':jday.weekday(),
            'in_person': 1 if usr.profile.in_person else 0
        }
        week_day = datetime.today().weekday() + 1
        item['availabilities'] = get_user_availability_for_day(usr,str(week_day))
        item['profile'] = usr.profile.image.url if usr.profile.image else '/static/img/avatar.png'
        item['url'] = usr.profile.get_absolute_url()
        item['records'] , item['sum_minutes'] , item['sum_inactive'] = get_day_records_for_user(usr,jday)
        item['vocations'] = get_day_vocations_for_user(usr,jday)
        if request.user == usr or request.user.is_staff:
            item['app_records'] = get_app_records_for_user(usr,jday)
            item['website_records'] = get_website_records_for_user(usr,jday)
            item['sum_words'] = get_sum_words_for_user(usr,jday)
        
        if request.user == usr:
            user_records.insert(0, item)
        else:
            user_records.append(item)

    jtoday = jday.date()
    d_from = datetime(jtoday.year,jtoday.month,jtoday.day,0,0,0)
    future_vocations = VocationRequest.objects.filter(start__gte=d_from)
    current_date = get_current_date_and_time()
    if not request.user.is_staff:
        return render(request , 'timetracker/index.html' ,locals() )
    
    # only for staff users
    start_date_sum = datetime(jtoday.year,jtoday.month,1,0,0,0)
    if jtoday.month == 12: 
        end_date_sum = datetime(jtoday.year+1,1,1,0,0,0)
    else:
        end_date_sum = datetime(jtoday.year,jtoday.month+1,1,0,0,0)
    sum_app_times = get_sum_time_for_apps(start_date_sum,end_date_sum)

    return render(request , 'timetracker/index.html' ,locals() )

month_names = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
]

week_days = [
    "شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"
]

def get_current_date_and_time():

    today = datetime.now()
    year = today.year
    month = today.month
    day = today.day
    weekday = week_days[today.weekday()]
    month_name = month_names[month - 1]

    current_date = f"{weekday} {day} {month_name} {year}"
    return current_date


def get_sum_time_for_apps(start_date,end_date,user=None):

    q_filter = Q(Q(work_record__start__gte=start_date)& Q(work_record__end__lt=end_date))
    if user:
        q_filter &= Q(work_record__user=user)

    sum_app_times = {}
    for app in RecordedApp.objects.filter(is_browser=False):
        sum_time = AppRecord.objects.filter(q_filter,app=app).aggregate(Sum('w_time'))['w_time__sum']
        if not sum_time or sum_time < 60:
            continue

        sum_app_times[app.name] = {
            'time':sum_time if sum_time else 0,
            'icon': app.icon.url if app.icon else 'null',#'/static/img/avatar.png'
            'name': app.name,
        }
    for website in RecordedWebsite.objects.all():
        sum_time = AppRecord.objects.filter(q_filter,website=website).aggregate(Sum('w_time'))['w_time__sum']
        if not sum_time or sum_time < 60:
            continue
        sum_app_times[website.name] = {
            'time':sum_time if sum_time else 0,
            'icon': website.icon.url if website.icon else 'null',#'/static/img/avatar.png',
            'name': website.name,
        }
    import json
    return json.dumps(sum_app_times)

def get_sum_words_for_user(usr,jday):
    
    rec_filters = Q(start__gte=datetime(jday.year,jday.month,jday.day,0,0,0)) & Q(start__lte=datetime(jday.year,jday.month,jday.day,23,59,59))
    recs = WorkRecord.objects.filter(rec_filters,user = usr).aggregate(Sum('sum_words'))
    sum_words = recs['sum_words__sum']
    if not sum_words:
        sum_words = 0
    return sum_words

def get_app_records_for_user(usr,jday):
    app_records = {}
    rec_filters = Q(start__gte=datetime(jday.year,jday.month,jday.day,0,0,0)) & Q(start__lte=datetime(jday.year,jday.month,jday.day,23,59,59))
    last_recs = WorkRecord.objects.filter(rec_filters,user = usr)
    for app_rec in AppRecord.objects.filter(work_record__in =last_recs  ,app__is_browser=False):
        if app_rec.app.name not in app_records:
            app_records[app_rec.app.name] = {
                'total':0,
                'icon': app_rec.app.icon.url if app_rec.app.icon else 'null',#'/static/img/avatar.png'
                'name': app_rec.app.name,
            }
        
        app_records[app_rec.app.name]['total'] += app_rec.w_time

    return app_records 


def get_website_records_for_user(usr,jday):
    app_records = {}
    rec_filters = Q(start__gte=datetime(jday.year,jday.month,jday.day,0,0,0)) & Q(start__lte=datetime(jday.year,jday.month,jday.day,23,59,59))
    last_recs = WorkRecord.objects.filter(rec_filters,user = usr)
    for app_rec in AppRecord.objects.filter(work_record__in =last_recs  ,app__is_browser=True):
        if app_rec.website.name not in app_records:
            app_records[app_rec.website.name] = {
                'total':0,
                'icon':app_rec.website.icon.url if app_rec.website.icon else 'null',#'/static/img/avatar.png''/static/img/avatar.png'
                'name':app_rec.website.name
            }        
        app_records[app_rec.website.name]['total'] += app_rec.w_time

    return app_records 


def get_day_records_for_user(usr,jday,request_user=None):
    sum_minutes = 0
    sum_inactive = 0
    all_sum_inactive = 0
    records = []
    rec_filters = Q(start__gte=datetime(jday.year,jday.month,jday.day,0,0,0)) & Q(start__lte=datetime(jday.year,jday.month,jday.day,23,59,59))
    last_recs = WorkRecord.objects.filter(rec_filters,user = usr)
    for r in last_recs:
        r_item = {'id':r.id,'start':str(r.start.time())[:5]}
        r_item['end'] = str(r.end.time())[:5] if r.end else "null"

        # calcuate sum working minutes
        diff = record_time(r)
        sum_minutes += diff

        
        if not r.end:
            # add inactive of running record to inactives
            sum_inactive += r.inactive_time
            # all_sum_inactive += r.inactive_time

        r_item['width'] = (diff / 1440)*100
        x = time.strptime(r_item['start'],'%H:%M')
        st_sum = edatetime.timedelta(hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec).total_seconds() // 60
        r_item['start_p'] = (int(st_sum) / 1440)*100
        r_item['inactive_times'] , r_sum_inactives = get_record_inactive_times(r)
        all_sum_inactive += r_sum_inactives
        if request_user and request_user.id == 1:
            r_item['editable']= 1
        records.append(r_item)

    records = sorted(records, key=lambda d: (d['start'],d['end']))
    sum_minutes = sum_minutes - (sum_inactive//60)
    return records , sum_minutes , all_sum_inactive



def check_record_last_updated(record):
    """
        check not ended records last updated
        add inactive to record inactives if not updated in last 15 minutes
    """
    if not record.last_updated or record.end:
        return
    tz = pytz.timezone('Asia/Tehran')
    now = tz.localize(datetime.now())
    min_not_updated = ( now - record.last_updated ).total_seconds() // 60
    # print(f'min_not_updated: {min_not_updated}')

    if int(min_not_updated) > 300:
        record.end = record.last_updated
        record.save()
        return 

    if int(min_not_updated) < 15:
        return

    new_inactive = {
        'start':str(record.last_updated.time())[:5],
        'end':'null',
        'width': (min_not_updated / 1440)*100
    }

    x = time.strptime(new_inactive['start'],'%H:%M')
    st_sum = edatetime.timedelta(hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec).total_seconds() // 60
    new_inactive['start_p'] = (int(st_sum) / 1440)*100
    return new_inactive


def get_record_inactive_times(record):
    list_inactive = []
    sum_inactive = 0
    new_inactive = check_record_last_updated(record)
    if new_inactive:
        list_inactive.append(new_inactive)
    for r in record.inactive_times.all().distinct():
        item = {
            'id':r.id ,
            'start':str(r.start.time())[:5] 
        }
        if r.end:
            item['end'] = str(r.end.time())[:5]
        else:
            if not record.last_updated :
                item['end'] = "null"
                continue

            tz = pytz.timezone('Asia/Tehran')
            now = tz.localize(datetime.now())
            min_not_updated = ( now - record.last_updated ).total_seconds() // 60
            print('__________________________________')
            print(f'min_not_updated: {min_not_updated} record: { str(record.start)} inactive start : { str(r.start) }')
            if int(min_not_updated) > 300:
                r.end = record.last_updated
                r.save()
                item['end'] = str(r.end.time())[:5]
            else:
                item['end'] = "null"

        diff = record_time(r)

        sum_inactive += diff
        item['width'] = (diff / 1440)*100
        x = time.strptime(item['start'],'%H:%M')
        st_sum = edatetime.timedelta(hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec).total_seconds() // 60
        item['start_p'] = (int(st_sum) / 1440)*100
        list_inactive.append(item)
    list_inactive = sorted(list_inactive, key=lambda d: (d['start'],d['end']))
    return list_inactive , sum_inactive


def get_day_vocations_for_user(usr,jday):
    vocations_list = []
    rec_filters = Q(start__gte=datetime(jday.year,jday.month,jday.day,0,0,0)) & Q(start__lte=datetime(jday.year,jday.month,jday.day,23,59,59))
    vocations = VocationRequest.objects.filter(rec_filters,user=usr)
    for v in vocations:
        v_item = {'start':str(v.start.time())[:5]}
        v_item['end'] = str(v.end.time())[:5]
        diff = record_time(v)
        v_item['width'] = (diff / 1440)*100
        x = time.strptime(v_item['start'],'%H:%M')
        st_sum = edatetime.timedelta(hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec).total_seconds() // 60
        v_item['start_p'] = (int(st_sum) / 1440)*100
        vocations_list.append(v_item)

    return vocations_list

@login_required(login_url='login')
def check_last_record_status(request):
    rec = WorkRecord.objects.filter(user = request.user).last()
    if rec and not rec.end:
        return JsonResponse({'success':True,'status':'unfinished'})
    return JsonResponse({'success':True,'status':'finished'})


def record_time(rec):
    start = rec.start.date()
    tz = pytz.timezone('Asia/Tehran')
    if rec.end:
        end = rec.end
    else:
        end = tz.localize(datetime.now())
    return ((end - rec.start ).total_seconds() // 60)


def start_recording(request):
    user = request.user 
    if not user.is_authenticated:
        return JsonResponse({'success':False,'msg':'شما از حساب خود خارج شده اید. باید دوباره وارد شوید.'})

    tz = pytz.timezone('Asia/Tehran')
    last_rec =  WorkRecord.objects.filter(user=user).last()
    if last_rec and not last_rec.end:
        return JsonResponse({'success':False})
    rec = WorkRecord.objects.create(
        user = request.user,
        start = tz.localize(datetime.now()),
    )
    return JsonResponse({'success':True ,'rec_id':rec.id})

@csrf_exempt
def stop_recording(request):
    user = request.user 
    if not user.is_authenticated:
        return JsonResponse({'success':False,'msg':'شما از حساب خود خارج شده اید. باید دوباره وارد شوید.'})

    rec = WorkRecord.objects.get(id=request.POST.get('rec_id'))
    if rec.end:
        msg = 'Record already ended'
        return JsonResponse({'success':False,'msg':msg})
    tz = pytz.timezone('Asia/Tehran')
    now = datetime.now()
    if rec.start.date() == now.date():
        rec.end = tz.localize(now)
    else:
        rec.end = tz.localize(datetime(rec.start.year, rec.start.month, rec.start.day,23,59,59))
        rec2 = WorkRecord.objects.create(
            user = user,
            start = tz.localize(datetime(now.year, now.month, now.day,0,0,0)) ,
            end = tz.localize(now)
        )
    rec.save()
    diff = rec.end - rec.start
    rec.w_time = str(diff)[:7]
    rec.save()
    return JsonResponse({'success':True})



@login_required(login_url='login')
def vocation_request(request):
    user = request.user
    if request.POST.get('type') == 'daily':
        v_type = 'روزانه'
    else:
        v_type = 'ساعتی'
    description = request.POST.get('description',None)
    date = request.POST.get('date').split('/')
    from_time = request.POST.get('from_time','00:00').split(':')
    to_time = request.POST.get('to_time','23:59').split(':')
    start = datetime(int(date[0]),int(date[1]),int(date[2]),int(from_time[0]),int(from_time[1]),0)
    end = datetime(int(date[0]),int(date[1]),int(date[2]),int(to_time[0]),int(to_time[1]),0)
    voc = VocationRequest.objects.create(
        user = user,
        v_type = v_type ,
        start = start,
        end = end ,
        description = description
    )
    return JsonResponse({'success':True})


def check_unfinished_record(rec,user):
    tz = pytz.timezone('Asia/Tehran')
    now = datetime.now()
    # unfinished record is for todays
    if rec.start.date() == now.date():
        unfinished_rec = rec
        return unfinished_rec
    rec.end = tz.localize(datetime(rec.start.year, rec.start.month, rec.start.day,23,59,59))
    rec.save()
    unfinished_rec = WorkRecord.objects.create(
        user =  user ,
        start = tz.localize(datetime(now.year, now.month, now.day,0,0,0)) ,
    )
    return unfinished_rec


@login_required(login_url='login')
def user_profile(request,username):
    try:
        user = User.objects.get(username=username)
    except:
        return HttpResponse('user does not exist')
    rec = WorkRecord.objects.filter(user = request.user).last()
    result = {
        'id':user.id,
        'name':user.first_name + ' ' + user.last_name ,
        'days': {}
    }
    result['profile'] = user.profile.image.url if user.profile.image else '/static/img/avatar.png'
    today = edatetime.datetime.now()
    for i in range(5):
        day = (today - timedelta(days = i)).date()
        jday = date.fromgregorian(date=day)
        result['days'][str(jday)] = {'records':[],'vocations':[],'sum_minutes':0,'sum_inactive':0,'weekday':jday.weekday()}
        result['days'][str(jday)]['records'] , result['days'][str(jday)]['sum_minutes'] , result['days'][str(jday)]['sum_inactive'] = get_day_records_for_user(user,jday,request.user)
        result['days'][str(jday)]['vocations'] = get_day_vocations_for_user(user,jday)
        if request.user == user or request.user.is_staff:
            result['days'][str(jday)]['app_records'] = get_app_records_for_user(user,jday)
            result['days'][str(jday)]['website_records'] = get_website_records_for_user(user,jday)
            result['days'][str(jday)]['sum_words'] = get_sum_words_for_user(user,jday)

    if request.user.is_staff or user == request.user :
        today = datetime.now().date()
        dt = date(today.year,today.month ,1)
        start_date = datetime(dt.year,dt.month,1,0,0,0)
        if dt.month == 12:
            end_date  = datetime(dt.year+1,1,1,0,0,0)
        else:
            end_date  = datetime(dt.year,dt.month+1,1,0,0,0) 
        statistics = calc_statistics(user,start_date,end_date)
        sum_app_times = get_sum_time_for_apps(start_date,end_date,user)
        # average inactive time
        tomorrow = datetime(dt.year,dt.month,dt.day+1,0,0,0)
        average_inactive = get_average_inactive_time(start_date,tomorrow,user)

    availability_times = get_availability_items(user)
    jtoday = datetime.now().date()
    d_from = datetime(jtoday.year,jtoday.month,jtoday.day,0,0,0)
    future_vocations = VocationRequest.objects.filter(start__gte=d_from)
    if request.user.username in ['admin','miladrastin'] :
        can_see_log = True
    return render(request , 'timetracker/profile.html' ,locals())




def get_availability_items(user):
    result = {}
    for i in range(1,8):
        j = str(i)
        result[j] = get_user_availability_for_day(user,j)
    return result

def get_user_availability_for_day(user,day):
    available_times = UserAvailability.objects.filter(user=user,week_day=day,is_available=True)
    result_item = {'available':[],'unavailable':[]}
    for item in available_times:
        result_item['available'].append({'id':item.id,'start':str(item.start)[:5],'end':str(item.end)[:5]})
    unavailable_times = UserAvailability.objects.filter(user=user,week_day=day,is_available=False)
    for item in unavailable_times:
        result_item['unavailable'].append({'id':item.id,'start':str(item.start)[:5],'end':str(item.end)[:5]})  
    return result_item


def calc_statistics(user,start_date,end_date):
    profile = user.profile
    worked_time = 0
    vocation_time = 0

    dt = start_date.date()

    # calcuate sum worked time in month
    rec_filters = Q(Q(start__gte=start_date) & Q(start__lt=end_date)) | Q(Q(end__gte=start_date) & Q(end__lt=end_date)) 
    for rec in WorkRecord.objects.filter(rec_filters,user = user):
        # get end
        tz = pytz.timezone('Asia/Tehran')
        end = rec.end if rec.end else tz.localize(datetime.now())
        
        if end.date().month != rec.start.date().month :
            if rec.start.month == dt.month:
                diff = ((end_date - rec.start ).total_seconds() // 60)
            elif end.month == dt.month:
                diff = ((end - start_date ).total_seconds() // 60)
        else:
            diff = ((end - rec.start ).total_seconds() // 60)
        worked_time += diff

    month_time = get_user_month_sum_time(profile,dt,end_date)

    # calcuate sum vocation time in month
    vocation_time = calc_user_vocation_in_month(user)
    if vocation_time >= (user.profile.vocation_in_month*60):
        vocation_time = user.profile.vocation_in_month*60

    month_mofid_time = vocation_time + worked_time
    month_time = month_time*60
    left_time = abs(month_mofid_time - month_time)
    sum_vocation = str(int(vocation_time // 60))+':'+str(int( vocation_time % 60))
    left_time    = str(int(left_time // 60))+':'+str(int( left_time % 60))
    sum_worked    = str(int(worked_time // 60))+':'+str(int( worked_time % 60))
    if month_time > month_mofid_time:
        left_time = '-'+left_time
    else:
        left_time = '+'+left_time
    return {'sum_vocation':sum_vocation,'sum_worked':sum_worked,'left_time':left_time}


def get_user_month_sum_time(profile,dt,end_date):
    # calcuate sum time must work in month
    month_time = 0
    today = datetime.now().date()
    while dt != end_date.date():
        
        # if day is holidy, do not calculate
        if HolidayDay.objects.filter(day = dt).exists():
            # print( dt,dt.weekday() )
            dt = dt + timedelta(days=1)
            continue

        w = dt.weekday()
        if w == 0:
            month_time += profile.saturday_time
        elif w == 1:
            month_time += profile.sunday_time
        elif w == 2:
            month_time += profile.monday_time
        elif w == 3:
            month_time += profile.tuesday_time
        elif w == 4:
            month_time += profile.wednesday_time
        elif w == 5:
            month_time += profile.thursday_time
        elif w == 6:
            month_time += profile.friday_time
        dt = dt + timedelta(days=1)

    return month_time

def calc_user_vocation_in_month(user):
    dt = datetime.now().date()
    start_date = datetime(dt.year,dt.month,1,0,0,0)
    if dt.month == 12:
        end_date  = datetime(dt.year+1,1,1,0,0,0)
    else:
        end_date  = datetime(dt.year,dt.month+1,1,0,0,0)
    vocation_time = 0
    v_filters = Q(Q(start__gte=start_date) & Q(start__lt=end_date))
    for v in VocationRequest.objects.filter(v_filters,user=user):
        if v.v_type == 'روزانه':
            diff = 60 * (user.profile.vocation_in_month // 2)
        else:
            diff = ((v.end - v.start ).total_seconds() // 60)
        vocation_time += diff
    return vocation_time


@login_required(login_url='login')
def load_more_day_records(request):
    try:
        user = User.objects.get(id=request.POST.get('user_id'))
    except:
        return JsonResponse({'success':False,'msg':'user does not exist'})
    if request.user != user or not request.user.is_superuser:
        JsonResponse({'success':False ,'msg':'You have not access to this page'})
    tim = int(request.POST.get('time'))*5
    result = {'days':{}}
    today = edatetime.datetime.now()
    for i in range(tim,(tim*3)+1):
        day = (today - timedelta(days = i)).date()
        jday = date.fromgregorian(date=day)
        result['days'][str(jday)] = {'records':[],'vocations':[],'sum_minutes':0,'sum_inactive':0,'weekday':jday.weekday()}
        result['days'][str(jday)]['records'] , result['days'][str(jday)]['sum_minutes'] , result['days'][str(jday)]['sum_inactive'] = get_day_records_for_user(user,jday)
        result['days'][str(jday)]['vocations'] = get_day_vocations_for_user(user,jday)
        if request.user == user or request.user.is_staff:
            result['days'][str(jday)]['app_records'] = get_app_records_for_user(user,jday)
            result['days'][str(jday)]['website_records'] = get_website_records_for_user(user,jday)
            result['days'][str(jday)]['sum_words'] = get_sum_words_for_user(user,jday)
    return JsonResponse({'success':True,'result':result})


@login_required(login_url='login')
def calc_reminded_vocation(request):
    user = request.user 
    vocation_time = calc_user_vocation_in_month(user)
    if vocation_time >= (user.profile.vocation_in_month*60):
        reminded = 0
    else:
        reminded = (user.profile.vocation_in_month*60) - vocation_time
    reminded = '%d ساعت و %d دقیقه'%(int(reminded // 60),int(reminded % 60))
    return JsonResponse({'success':True,'reminded':reminded})


def update_users_last_record(request):
    user = request.user 
    if not user.is_authenticated:
        return JsonResponse({'success':False,'loggedout':True,'msg':'شما از حساب خود خارج شده اید. باید دوباره وارد شوید.'})

    users = []
    jday = datetime.now()

    if not request.user.is_staff:
        # not staff users only seen themselves
        user_objs = User.objects.filter(profile__isnull=False,id=request.user.id)
    else:
        user_objs = User.objects.filter(profile__isnull=False)

    for user in user_objs:
        item = {'id':user.id}
        item['records'] , item['sum_minutes'] , item['sum_inactive'] = get_day_records_for_user(user,jday)
        item['vocations'] = get_day_vocations_for_user(user,jday)
        if request.user == user or request.user.is_staff:
            item['app_records'] = get_app_records_for_user(user,jday)
            item['website_records'] = get_website_records_for_user(user,jday)
            item['sum_words'] = get_sum_words_for_user(user,jday)
        
        if request.user == user:
            users.insert(0, item)
        else:
            users.append(item)
    return JsonResponse({'success':True,'users':users})


@login_required(login_url='login')
def update_record_time(request):

    try:
        rec = WorkRecord.objects.get(id=request.POST.get('id'))
    except:
        return JsonResponse({'success':False,'msg':'record does not exist.'})
    if rec.user != request.user:
        return JsonResponse({'success':False,'msg':'You jave not premission to edit this record.'})
    
    start = request.POST.get('start')
    end = request.POST.get('end')
    if end != "" and datetime.strptime(start,'%H:%M') > datetime.strptime(end,'%H:%M'):
        return JsonResponse({'success':False,'msg':'زمان شروع باید کوچکتر از زمان پایان باشد.'})
    if end == "" and datetime.strptime(start,'%H:%M').time() > datetime.now().time():
        return JsonResponse({'success':False,'msg':'زمان شروع باید کوچکتر از زمان فعلی سیستم باشد.'})

    rec.start = rec.start.replace(hour =int(start.split(':')[0]),minute=int(start.split(':')[1]))
    if end != "":
        try:
            rec.end = rec.end.replace(hour =int(end.split(':')[0]),minute=int(end.split(':')[1]))
        except:
            rec.end = datetime.now().replace(hour =int(end.split(':')[0]),minute=int(end.split(':')[1]))

    rec.save()
    return JsonResponse({'success':True})



@login_required(login_url='login')
def save_courses_image(request,username):
    try:
        user = User.objects.get(username=username)
    except:
        return HttpResponse('User does not exist')

    if request.method != 'POST':
        return HttpResponse('Request is not valid')

    if user != request.user and not request.user.is_superuser:
        return HttpResponse('You have not access to this action')

    courses_image = request.FILES['courses_image']
    user.profile.courses_image = courses_image
    user.profile.save()
    return redirect('user_profile',user.username)


@login_required(login_url='login')
def delete_availability_time(request):
    if request.method != 'POST' :
        return JsonResponse({'success':False,'msg': 'request is not valid'})
    try:
        obj = UserAvailability.objects.get(id=request.POST['id'])
    except:
        return JsonResponse({'success':False,'msg': 'item does not exist'})
    user = request.user
    if not(obj.user == user or user.is_superuser):
        return JsonResponse({'success':False,'msg': 'You have not access to this action'})
    obj.delete()
    return JsonResponse({'success':True,'msg': 'حذف با موفقیت انجام شد.'})


@login_required(login_url='login')
def add_availability_time(request):

    if request.method != 'POST' :
        return JsonResponse({'success':False,'msg': 'request is not valid'})
    start = request.POST['start']
    end = request.POST['end']
    week_day = request.POST['day']
    is_available = request.POST['av_type']
    user_id = int(request.POST['user_id'])
    
    user = request.user
    if not(user_id == user.id or user.is_superuser):
        return JsonResponse({'success':False,'msg': 'You have not access to this action'})

    if not(start and end and week_day and is_available):
        return JsonResponse({'success':False,'msg': 'required fields must be filled'})


    is_available = True if is_available == 'available' else False    
    obj = UserAvailability.objects.create(
        user_id=user_id,
        start = start ,
        end = end ,
        week_day=week_day,
        is_available = is_available
    )

    return JsonResponse({'success':True,'created_id':obj.id,'msg': 'علمیات با موفقیت انجام شد'})


@login_required(login_url='login')
def sum_month_report(request):
    if not(request.user.is_superuser or request.user.is_staff) :
         return JsonResponse({'success':False,'msg': 'You have not access'})
    start_date = request.POST.get('start')
    start_date_sum = datetime.strptime(start_date, '%Y/%m/%d')
    end_date = request.POST.get('end')
    end_date_sum = datetime.strptime(end_date, '%Y/%m/%d') + +timedelta(days=1)
    sum_app_times = get_sum_time_for_apps(start_date_sum,end_date_sum)
    return JsonResponse({'success':True,'sum_app_times': sum_app_times})


@login_required(login_url='login')
def sum_profile_report(request):
    user_id = request.POST.get('user')
    try:
        user = User.objects.get(id=request.POST.get('user_id'))
    except:
        return JsonResponse({'success':False,'msg':'user does not exist'})
    if not(request.user.is_superuser or request.user.is_staff or user==request.user) :
         return JsonResponse({'success':False,'msg': 'You have not access'})
    start_date = request.POST.get('start')
    start_date_sum = datetime.strptime(start_date, '%Y/%m/%d')
    end_date = request.POST.get('end')
    end_date_sum = datetime.strptime(end_date, '%Y/%m/%d') + +timedelta(days=1)

    # sum app times
    sum_app_times = get_sum_time_for_apps(start_date_sum,end_date_sum,user)

    # average inactive time
    average_inactive = get_average_inactive_time(start_date_sum,end_date_sum,user)

    jday = start_date_sum.date()
    days_records = {}
    while jday != end_date_sum.date():
        days_records[str(jday)] = {'records':[],'vocations':[],'sum_minutes':0,'sum_inactive':0,'weekday':jday.weekday()}
        days_records[str(jday)]['records'] , days_records[str(jday)]['sum_minutes'] , days_records[str(jday)]['sum_inactive'] = get_day_records_for_user(user,jday,request.user)
        days_records[str(jday)]['vocations'] = get_day_vocations_for_user(user,jday)
        if request.user == user or request.user.is_staff:
            days_records[str(jday)]['app_records'] = get_app_records_for_user(user,jday)
            days_records[str(jday)]['website_records'] = get_website_records_for_user(user,jday)
            days_records[str(jday)]['sum_words'] = get_sum_words_for_user(user,jday)
        jday = jday + timedelta(days = 1)
    statistics = calc_statistics(user,start_date_sum,end_date_sum)

    return JsonResponse({
        'success':True,
        'sum_app_times': sum_app_times,
        'days_records':days_records,
        'statistics':statistics,
        'average_inactive':average_inactive
    })

@transaction.atomic
@login_required(login_url='login')
def delete_user_record(request):
    if not request.user.is_superuser  :
        return JsonResponse({'success':False,'msg': 'You have not access'})

    id = request.POST['id']
    user_id = request.POST['user']
    if request.POST['type'] == 'work':
        obj = get_object_or_404(WorkRecord,id=id,user=user_id)
    elif request.POST['type'] == 'inactive':
        return JsonResponse({'success':True})
        obj = get_object_or_404(RecordInactiveTime,id=id)
        if obj.work_record.user.id != int(user_id) :
            return JsonResponse({'success':False,'msg':'Unvalid Request.'})   
    else:
        return JsonResponse({'success':False,'msg':'Unvalid Request.'})
    
    obj.delete()
    return JsonResponse({'success':True,'msg':'حذف با موفقیت انجام شد.'})


from django.db.models import Func, ExpressionWrapper, F, FloatField, Sum, Q

from django.db import connection

def get_average_inactive_time(start_date,end_date,user):
    days = (end_date - start_date).days

    q_filter = Q(Q(start__gte=start_date)& Q(end__lt=end_date))
    q_filter &= Q(work_record__user=user)

    qs = RecordInactiveTime.objects.filter(q_filter)
    if not qs:
        return '00:00'
    
    db_type = connection.vendor
    if db_type == 'postgresql':
        qs = qs.annotate(
            duration_seconds=ExpressionWrapper(
                Func(F('end') - F('start'), function='EXTRACT', template="EXTRACT(EPOCH FROM %(expressions)s)"),
                output_field=FloatField()
            )
        ).annotate(
            duration_minutes=ExpressionWrapper(
                F('duration_seconds') / 60.0,
                output_field=FloatField()
            )
    )
    else:
        qs = qs.annotate(
            duration=ExpressionWrapper(
                F('end') - F('start'),
                output_field=DurationField()
            )
        ).annotate(
            duration_minutes=ExpressionWrapper(
                F('duration') / timedelta(minutes=1),
                output_field=FloatField()
            )
        )

    total_minutes = qs.aggregate(
        total_minutes=Sum('duration_minutes')
    )['total_minutes'] or 0
    # print(total_minutes)
    min_per_day = total_minutes // days
    return minutes_to_time_str(min_per_day) 


def minutes_to_time_str(total_minutes):
    hours, minutes = divmod(int(total_minutes), 60)
    return f"{hours:02}:{minutes:02}"


def user_logs(request,username):

    # check permission
    if not request.user.username in ['admin','miladrastin']:
        return HttpResponse('Access Denied.')
    
    # get user
    try:
        user = User.objects.get(username=username)
    except:
        return HttpResponse('user does not exist')

    num_record_to_load = 10000
    logs = RecordLog.objects.filter(work_record__user=user).order_by('-created')[:num_record_to_load]
    return render(request , 'timetracker/user_logs.html' ,{'logs':logs})
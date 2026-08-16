from calendar import FRIDAY, MONDAY, SATURDAY, SUNDAY, THURSDAY, TUESDAY, WEDNESDAY
from django.db import models
from django.contrib.auth.models import User
from django_jalali.db import models as jmodels
from django.urls import reverse 

from random import randint

def profile_image(instance, filename):
    return '/'.join(['profile_images/',str(instance.user.pk), str(randint(10000000, 99999999)) + '.jpg' ])

def courses_image_func(instance, filename):
    return '/'.join(['courses_image/',str(instance.user.pk), str(randint(10000000, 99999999)) + '.jpg' ])


class SystemConfig(models.Model):
    allowed_inactive_time = models.IntegerField(default=30,verbose_name='حداکثر زمان غیر فعالیت کارمندان غیرحضوری(دقیقه)')
    allowed_inactive_time_in_person = models.IntegerField(default=30,verbose_name='حداکثر زمان غیر فعالیت کارمندان حضوری(دقیقه)')
    
    def __str__(self):
        return f"تنظیمات"
    
    class Meta:
        db_table = 'system_config'
        verbose_name = "تنظمیات سیستم"
        verbose_name_plural = "تنظمیات سیستم"

class UserProfile(models.Model):
    # Relations
    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name='profile',verbose_name='کاربر')

    # Fields
    image = models.ImageField(upload_to=profile_image, blank=True, null=True,verbose_name='عکس پروفایل')
    courses_image = models.ImageField(upload_to=courses_image_func, blank=True, null=True,verbose_name='عکس انتخاب واحد')
    in_person = models.BooleanField(default=False,verbose_name='کارمند حضوری')
    inactive_time_delete_min = models.IntegerField(default=0,verbose_name=' حذف غیرفعال بیشتر از n دقیقه')
    saturday_time = models.IntegerField(verbose_name='تایم کاری شنبه',default=0,null=True)
    sunday_time = models.IntegerField(verbose_name='تایم کاری یکشنبه',default=0,null=True) 
    monday_time = models.IntegerField(verbose_name='تایم کاری دوشنبه',default=0,null=True)
    tuesday_time = models.IntegerField(verbose_name='تایم کاری سه شنبه',default=0,null=True)
    wednesday_time = models.IntegerField(verbose_name='تایم کاری چهارشنبه',default=0,null=True)
    thursday_time = models.IntegerField(verbose_name='تایم کاری پنجشنبه',default=0,null=True)
    friday_time = models.IntegerField(verbose_name='تایم کاری جمعه',default=0,null=True)
    vocation_in_month = models.IntegerField(verbose_name='تعداد ساعت مرخصی در ماه',null=True,blank=True)
    
    def save(self, *args, **kwargs):
        if not self.vocation_in_month:
            self.vocation_in_month = self.saturday_time * 2
        super(UserProfile, self).save(*args, **kwargs)

    def get_absolute_url(self):  
           return reverse('user_profile', args=[self.user.username,])

    def __str__(self):
        return self.user.username

    class Meta:
        db_table = 'user_profile'
        verbose_name = "پروفایل"
        verbose_name_plural = "پروفایل ها"


from django.db.models import Sum, F, ExpressionWrapper, DurationField
class WorkRecord(models.Model):
     # Relations
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='work_records',verbose_name='کاربر')
    p_record = models.ForeignKey('self', on_delete=models.CASCADE , related_name='sub_records',null=True,blank=True) 
    # Fields
    start = jmodels.jDateTimeField(verbose_name='شروع')
    end = jmodels.jDateTimeField(null=True , blank=True,verbose_name='پایان')
    w_time = models.TimeField(verbose_name='مدت زمان',null=True,blank=True,editable=False)
    inactive_time = models.PositiveIntegerField(verbose_name='زمان غیر فعالیت',default=0,null=True,blank=True)
    sum_words = models.PositiveIntegerField(verbose_name='تعداد کلمات',default=0,null=True,blank=True)
    is_updated = models.BooleanField(default=False)
    last_updated = jmodels.jDateTimeField(null=True , blank=True,verbose_name='آخرین بروزرسانی')

    def __str__(self):
        if self.user.first_name:
            return self.user.first_name+' '+self.user.last_name +'('+str(self.start)+')'
        else:
            return self.user.username +'('+str(self.start.date())+')' 
    
    class Meta:
        db_table = 'work_records'
        verbose_name = "ساعت کاری"
        verbose_name_plural = "ساعات کاری"

    def total_inactive_time_minutes(self):
        inactive_times = self.inactive_times.filter(end__isnull=False)
        duration_expression = ExpressionWrapper(
            F('end') - F('start'),
            output_field=DurationField()
        )
        total_duration = inactive_times.annotate(duration=duration_expression).aggregate(total_duration=Sum('duration'))['total_duration']

        # Convert total duration to minutes
        if total_duration:
            return total_duration.total_seconds() // 60
        return 0


class AppRecord(models.Model):
     # Relations
    work_record = models.ForeignKey('WorkRecord', on_delete=models.CASCADE,related_name='app_records')
    app = models.ForeignKey('RecordedApp', on_delete=models.CASCADE,related_name='records')
    website = models.ForeignKey('RecordedWebsite', on_delete=models.CASCADE,related_name='records',null=True,blank=True)
    
    # Fields
    w_time = models.PositiveIntegerField(verbose_name='مدت زمان به ثانیه',null=True,blank=True,editable=False)
    
    def __str__(self):
        if self.website:
            return self.app.name +' ('+str(self.website.name)+')'
        else:
            return self.app.name 

    class Meta:
        db_table = 'app_record'
        verbose_name = "زمان کاری با برنامه"
        verbose_name_plural = "زمان کاری با برنامه"

class RecordInactiveTime(models.Model):
     # Relations
    work_record = models.ForeignKey('WorkRecord', on_delete=models.CASCADE,related_name='inactive_times')

    # Fields
    start = jmodels.jDateTimeField(verbose_name='شروع')
    end = jmodels.jDateTimeField(null=True , blank=True,verbose_name='پایان')

    def __str__(self):
        return self.work_record.user.username +' ('+str(self.start)+')'


    class Meta:
        db_table = 'record_inactive_time'
        verbose_name = "زمان غیرفعال"
        verbose_name_plural = "زمان های غیرفعال "


class RecordLog(models.Model):
     # Relations
    work_record = models.ForeignKey('WorkRecord', on_delete=models.CASCADE,related_name='logs')

    # Fields
    text = models.TextField(null=True)
    created = jmodels.jDateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return self.work_record.user.username +' ('+str(self.work_record.id)+')'


    class Meta:
        db_table = 'record_log'
        verbose_name = "لاگ کاری"
        verbose_name_plural = "لاگ کاری"


class RecordedApp(models.Model):
    name =  models.CharField(max_length=70,verbose_name='نام')
    is_browser = models.BooleanField(verbose_name='مرورگر',default=False)
    icon = models.ImageField(upload_to='recorded_apps/', blank=True, null=True,verbose_name='آیکون')

    def __str__(self):
        return self.name 

    class Meta:
        db_table = 'recorded_app'
        verbose_name = "برنامه"
        verbose_name_plural = "ردیابی-برنامه ها"

class RecordedWebsite(models.Model):
    name =  models.CharField(max_length=70,verbose_name='نام')
    domain = models.CharField(max_length=100,verbose_name='آدرس دامنه')
    icon = models.ImageField(upload_to='recorded_websites/', blank=True, null=True,verbose_name='آیکون')

    def __str__(self):
        return self.name     

    class Meta:
        db_table = 'recorded_website'
        verbose_name = "سایت"
        verbose_name_plural = "ردیابی-سایت ها"


class VocationRequest(models.Model):
    type_choices = [
        ('روزانه', 'روزانه'),
        ('ساعتی', 'ساعتی'),
    ]
    # Relations
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='vocations',verbose_name='کاربر')

    # Fields
    v_type =  models.CharField(verbose_name='نوع مرخصی',max_length=25,choices=type_choices,null=True)
    description = models.TextField(verbose_name='توضیحات',null=True,blank=True)
    start = jmodels.jDateTimeField(verbose_name='شروع')
    end   = jmodels.jDateTimeField(verbose_name='پایان')

    def __str__(self):
        if self.user.first_name:
            return self.user.first_name+' '+self.user.last_name +'('+str(self.start.date())+')'
        else:
            return self.user.username +'('+str(self.start.date())+')'

    class Meta:
        db_table = 'vocation_requests'
        verbose_name = "درخواست مرخصی"
        verbose_name_plural = "درخواست های مرخصی"



class HolidayDay(models.Model):

    # Fields
    day = jmodels.jDateField(null=True)
    is_holiday = models.BooleanField(default=False)
    is_friday   =  models.BooleanField(default=False)

    class Meta:
        db_table = 'holiday_days'

class UserAvailability(models.Model):
    SATURDAY = '1'
    SUNDAY = '2'
    MONDAY = '3'
    TUESDAY = '4'
    WEDNESDAY = '5'
    THURSDAY = '6'
    FRIDAY = '7'
    WEEK_DAYS = [
        (SATURDAY, 'saturday'),
        (SUNDAY, 'sunday'),
        (MONDAY, 'monday'),
        (TUESDAY, 'tuesday'),
        (WEDNESDAY, 'wednesday'),
        (THURSDAY, 'thursday'),
        (FRIDAY, 'friday'),
    ]
    # Relations
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='availabilities',verbose_name='کاربر')

    # Fields
    week_day =  models.CharField(max_length=25,choices=WEEK_DAYS,null=True)
    is_available = models.BooleanField(default=True)
    start = models.TimeField(null=True,blank=True)
    end = models.TimeField(null=True,blank=True)



class UserError(models.Model):
     # Relations
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='erros',verbose_name='کاربر')
    record = models.ForeignKey('self', on_delete=models.CASCADE , related_name='errors',null=True,blank=True) 

    # Fields
    error_text = models.TextField(verbose_name='متن خطا',null=True,blank=True)
    json_text = models.TextField(verbose_name='جیسون ارسالی',null=True,blank=True)
    created = jmodels.jDateTimeField(auto_now_add=True, editable=False)


    def __str__(self):
        if self.user.first_name:
            return self.user.first_name+' '+self.error_text
        else:
            return self.user.username+' '+self.error_text
    
    class Meta:
        db_table = 'user_errors'
        verbose_name = "خطا"
        verbose_name_plural = "خطاهای کاربران"
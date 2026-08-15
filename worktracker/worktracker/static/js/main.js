

var refreshIntervalId ;
var rec_id ;
const monthNames = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "اذر", "دی", "بهمن", "اسفند"];
const weeDayNames = ['شنبه','یکشنبه','دوشنبه','سه شنبه','چهارشنبه','پنجشنبه','جمعه'];
const timer_update_mili_second = 1000;
const timer_update_users_last_record = 10000;
var title_interval;


// update page title 
function update_page_title(status,start_date=null){
    if(status=='online'){
        $("#favicon").attr("href","/static/img/online.png");
        title_interval = setInterval(function () {
            current_date = new Date();
            const diffTime = Math.abs(current_date - start_date);
            const diffSecs = Math.ceil(diffTime / (1000)); 
            title = 'آنلاین ، '
            title +=parseInt(diffSecs / 3600, 10) + ' ساعت ';
            title +=parseInt(diffSecs / 60, 10) % 60 +' دقیقه';
            $('title').html(title)
        }, timer_update_mili_second);  
    }
    else{
        clearInterval(title_interval);
        $("#favicon").attr("href","/static/img/offline.png");
        $('title').html('آفلاین')
    }
}


// load users records
function load_user_records(user_records){
    console.log(user_records)
    user_records.forEach(item => {
        $employee = $('#clone_data .employee-timetracker').clone()

        $employee.attr('href',item.url)
        $employee.attr('id','employee-'+item.id);
        if(item.in_person){
            $employee.addClass('in-person');
        }
        $('.body-timetracker').append($employee);

        $employee.find('.profile-image').attr('src',item.profile)
        $employee.find('.username').text(item.name);

        hour = parseInt(item.sum_minutes / 60, 10);
        minute = item.sum_minutes % 60;
        sum_time = ("0" + hour.toString()).substr(-2) +':'+ ("0" + minute.toString()).substr(-2) + ' ساعت'
        $employee.find('.sum-time').text(sum_time);

        hour = parseInt(item.sum_inactive / 60, 10);
        minute = item.sum_inactive % 60;
        sum_inactive = ("0" + hour.toString()).substr(-2) +':'+ ("0" + minute.toString()).substr(-2) + ' ساعت'
        $employee.find('.sum-inactive-time').text(sum_inactive);

        if(item.records.length > 0 ){
            last = item.records[item.records.length - 1];
            if(last.end != "null"){
                txt = 'آخرین فعالیت از '+ last.start + ' تا '+last.end;
            }
            else{
                txt = 'شروع کار از '+ last.start ;
                $employee.find('.is-offline').remove()
                $employee.find('.username').append($('<i class="is-online"></i>'))
            }
            $employee.find('.last-record-time').text(txt);
        }
        if(item.sum_words)$employee.find('.sum-words span').text(item.sum_words);
        else $employee.find('.sum-words').remove()
        
        add_records_to_employee(item.records,$employee)
        add_vocations_to_employee(item.vocations,$employee)
        add_app_records_to_employee(item.app_records,$employee)
        add_website_records_to_employee(item.website_records,$employee)
        add_availabilities_records_to_employee(item.availabilities.available,$employee)
        add_unavailabilities_records_to_employee(item.availabilities.unavailable,$employee);        
    });
}
function add_unavailabilities_records_to_employee(unavailable,$employee){
    unavailable.forEach(item => {
        // time line
        $el = $('<div class="unavailable-record"></div>');
        st_sum = (parseInt(item.start.split(':')[0])*60) + parseInt(item.start.split(':')[1])
        start_p = (st_sum / 1440)*100
        $el.css('left',start_p+'%');
        diff = total_minutes_between_times(item.start,item.end)
        width = (diff / 1440)*100
        $el.css('width',width +'%');
        txt = 'خارج از دسترس : '+ item.start +  ' الی ' + item.end
        $el.attr('aria-label',txt)
        $employee.find('.timeline-employee').append($el)
        // text
        $av_box = $('#clone_data').find('.unavailability-item').clone()
        $av_box.find('button').remove()
        $employee.find('.unavailabilities').append($av_box)
        txt = `${item.start} الی ${item.end}`
        $av_box.find('span').text(txt);
    })
}


function add_availabilities_records_to_employee(available,$employee){
    $employee.append($('#clone_data').find('.contain-available').clone())
    available.forEach(item => {
        // time line
        $el = $('<div class="available-record"></div>');
        st_sum = (parseInt(item.start.split(':')[0])*60) + parseInt(item.start.split(':')[1])
        start_p = (st_sum / 1440)*100
        $el.css('left',start_p+'%');
        diff = total_minutes_between_times(item.start,item.end)
        width = (diff / 1440)*100
        $el.css('width',width +'%');
        txt = 'در دسترس  : '+ item.start +  ' الی ' + item.end
        $el.attr('aria-label',txt)
        $employee.find('.timeline-employee').append($el);
        // text
        $av_box = $('#clone_data').find('.availability-item').clone()
        $av_box.find('button').remove()
        $employee.find('.availabilities').append($av_box)
        txt = `${item.start} الی ${item.end}`
        $av_box.find('span').text(txt);
    })
}

function add_website_records_to_employee(website_records,$employee){
    $website_records = $employee.find('.website-records')
    $.each(website_records, function (website_name,obj) {
        $app_record = $('#clone_data .app-record').clone()
        $website_records.append($app_record);
        sum_minutes = parseInt(obj.total / 60) ;
        hour = parseInt(sum_minutes / 60, 10);
        minute = sum_minutes % 60;
        sum_time = ("0" + hour.toString()).substr(-2) +':'+ ("0" + minute.toString()).substr(-2) 
        $app_record.find('span').text(sum_time);
        if(obj.icon == 'null'){
            $app_record.find('.app-icon').html(obj.name);
        }
        else{
            $app_record.find('img').attr('src',obj.icon);
        }

    });
 }


function add_app_records_to_employee(app_records,$employee){
    $app_records = $employee.find('.app-records');
    $.each(app_records, function (app_name,obj) {
        $app_record = $('#clone_data .app-record').clone()
        $app_records.append($app_record);
        sum_minutes = parseInt(obj.total / 60) ;
        hour = parseInt(sum_minutes / 60, 10);
        minute = sum_minutes % 60;
        sum_time = ("0" + hour.toString()).substr(-2) +':'+ ("0" + minute.toString()).substr(-2) 
        $app_record.find('span').text(sum_time);
        if(obj.icon == 'null'){
            $app_record.find('.app-icon').html(obj.name);
        }
        else{
            $app_record.find('img').attr('src',obj.icon);
        }

    });
 }


function add_records_to_employee(records,$employee){
    records.forEach(record => {
        $el = $('<div class="work-record"></div>');
        $el.css('left',record['start_p']+'%');
        $el.css('width',record['width']+'%');
        txt = 'شروع : '+ record['start']
        if(record['end'] != 'null')
            txt+= ' , پایان : ' + record['end']
        $el.attr('aria-label',txt)
        $employee.find('.timeline-employee').append($el)
        
        record.inactive_times.forEach(inactive_record => {
            $el = $('<div class="inactive-record"></div>');
            $el.css('left',inactive_record['start_p']+'%');
            $el.css('width',inactive_record['width']+'%');
            txt = 'غیرفعال، شروع : '+ inactive_record['start']
            if(inactive_record['end'] != 'null')
                txt+= ' , پایان : ' + inactive_record['end']
            else{
                $employee.find('.is-online').remove()
                $employee.find('.username').append($('<i class="is-offline"></i>'))
            }
            $el.attr('aria-label',txt)
            $employee.find('.timeline-employee').append($el)
        });
    });
 }
 

function add_vocations_to_employee(vocations,$employee){
    vocations.forEach(vocation => {
        $el = $('<div class="vocation-record"></div>');
        $el.css('left',vocation['start_p']+'%');
        $el.css('width',vocation['width']+'%');
        txt = 'شروع : '+ vocation['start'] +  ' , پایان : ' + vocation['end']
        $el.attr('aria-label',txt)
        $employee.find('.timeline-employee').append($el)
    });
 }


// show current date and time
function show_current_date_and_time(){
    var span = document.getElementById('current_time');
    // let now = new JalaliDate();
    // let dayOfWeek = now.getDay();
    // let today = weeDayNames[dayOfWeek] + " " + now.getDate() +" "+ monthNames[now.getMonth()];
    $('#current_date').text(current_jdate);
    function time() {
        var d = new Date();
        var s = d.getSeconds();
        var m = d.getMinutes();
        var h = d.getHours();
        span.textContent = 
            ("0" + h).substr(-2) + ":" + ("0" + m).substr(-2) + ":" + ("0" + s).substr(-2);
    }
    refreshIntervalId = setInterval(time, 1000);

    update_page_title('offline')
    needToConfirmExitPage = false;
}


// show started time 
function show_started_time(start_time=null){
    clearInterval(refreshIntervalId)
    var span = document.getElementById('current_time');
    if(start_time){
        span.textContent = "شروع از " + start_time
    }
    else{
    var d = new Date();
    var s = d.getSeconds();
    var m = d.getMinutes();
    var h = d.getHours();
    span.textContent = "شروع از " +
        ("0" + h).substr(-2) + ":" + ("0" + m).substr(-2) ;   
    }
    // let now = new JalaliDate();
    // let dayOfWeek = now.getDay(); 
    // // dayOfWeek = (dayOfWeek + 6) % 7;
    // let today = weeDayNames[dayOfWeek] + " " + now.getDate() +" "+ monthNames[now.getMonth()];
    $('#current_date').text( current_jdate);
}


// start recording
function start_recording(sum_minutes=null,start_time=null){    
    if(start_time){
        show_started_time(start_time);
    }
    else{
        return 
        res = request_ajax('/ajax/start-recording' , {start:true});
        if(!res['success']) location.reload();
        rec_id = res['rec_id'];
        show_started_time();
    }

    $stop = $('#clone_data .btn-stop-tracking').clone()
    $('.btn-start-stop').html($stop);
    start_date = new Date();
    if(sum_minutes){
        var hours = Math.floor(sum_minutes / 60);          
        var minutes = sum_minutes % 60;
        start_date.setHours(start_date.getHours() - hours);
        start_date.setMinutes(start_date.getMinutes() - minutes);
    }
    console.log(start_date)
    setInterval(function () {
        current_date = new Date();
        const diffTime = Math.abs(current_date - start_date);
        const diffSecs = Math.ceil(diffTime / (1000)); 
        $stop.find("#seconds").html(parseInt(diffSecs % 60) + ' ثانیه ');
        $stop.find("#minutes").html(parseInt(diffSecs / 60, 10) % 60 +' دقیقه');
        $stop.find("#hours").html(parseInt(diffSecs / 3600, 10) + ' ساعت ');
    }, timer_update_mili_second);
    update_page_title('online',start_date)   
    needToConfirmExitPage = true;
}



// stop recording
function stop_recording(){
    res = request_ajax('/ajax/stop-recording' , {stop:true,rec_id:rec_id});
    if(!res['success']) return;
    show_current_date_and_time()
    $('.btn-start-stop').html('');

    // $start = $('#clone_data .btn-start-tracking').clone()
    // $('.btn-start-stop').html($start);
    var sec = -1; 
   
}


// pad time
function pad(val) {
    var valString = val + "";
    if (valString.length < 2) {
        return "0" + valString;
    } else {
        return valString;
    }
}

function call_datepicker(element){
    element.persianDatepicker({
        cellWidth: 35,
        cellHeight: 30,
    });
}

function add_vocation_request(type){
    $('.head-timetracker .vocation-request-box').remove()
    $v_box = $('#clone_data .vocation-request-box').clone()
    if(type=='daily'){
        $v_box.find('.time-box').remove()
    }
    res = request_ajax('/ajax/calc-reminded-vocation')
    if(!res.success) return;
    $v_box.find('.reminded').text('باقی مانده مرخصی در این ماه : '+res.reminded)
    call_datepicker($v_box.find('.vocation-date-inpt'));
    $('.head-timetracker').append($v_box);
    $v_box.find('.submit-req').click(function(){
        v_date = $v_box.find('input[name="v_date"]').val();
        if(v_date == ''){
            alert('فیلد تاریخ مرخصی را انتخاب کنید.')
            return
        }
        var req_data = {
            type:type,
            date: v_date ,
            description: $v_box.find('textarea[name="description"]').val()
        }
        if(type=='hourly'){
            from_time = $v_box.find('input[name="from_time"]').val();
            to_time = $v_box.find('input[name="to_time"]').val();
            if(from_time == '' || to_time == ''){
                alert('لطفا ساعت مرخصی را انتخاب کنید.')
                return
            }
            req_data['from_time'] = from_time;
            req_data['to_time'] = to_time;
        }
        res = request_ajax('/ajax/vocation-request' , req_data)
        if(res['success']){
            $v_box.remove()
            alert('درخواست مرخصی شما با موفقیت ثبت شد.')
        } 
        console.log(res)
    
   
    })
    $v_box.find('.close').click(function(){
        $v_box.remove()
    })
}
          
function update_users_last_record(){
    res = request_ajax('/ajax/update-users-last-record')
    if(!res['success'] && res['loggedout']) clearInterval(update_users_interval);
    if(!res.success) return;
    res.users.forEach(item => {
        $employee = $('#employee-'+item.id)
        hour = parseInt(item.sum_minutes / 60, 10);
        minute = item.sum_minutes % 60;
        sum_time = ("0" + hour.toString()).substr(-2) +':'+ ("0" + minute.toString()).substr(-2) + ' ساعت'
        $employee.find('.sum-time').text(sum_time);

        hour = parseInt(item.sum_inactive / 60, 10);
        minute = item.sum_inactive % 60;
        sum_inactive = ("0" + hour.toString()).substr(-2) +':'+ ("0" + minute.toString()).substr(-2) + ' ساعت'
        $employee.find('.sum-inactive-time').text(sum_inactive);

        if(item.records.length > 0 ){
            last = item.records[item.records.length - 1];
            if(last.end != "null"){
                txt = 'آخرین فعالیت از '+ last.start + ' تا '+last.end;
                $employee.find('.is-online').remove()
                $employee.find('.is-offline').remove()
            }
            else{
                txt = 'شروع کار از '+ last.start ;
                $employee.find('.is-offline').remove()
                if(!$employee.find('.is-online').length)
                    $employee.find('.username').append($('<i class="is-online"></i>'))
            }
            $employee.find('.last-record-time').text(txt);
        }
        if(item.sum_words)$employee.find('.sum-words span').text(item.sum_words);
        $employee.find('.work-record').remove()
        $app_records = $employee.find('.app-records')
        $app_records.html("");
        $website_records = $employee.find('.website-records')
        $website_records.html("");

        add_records_to_employee(item.records,$employee)
        add_app_records_to_employee(item.app_records,$employee)
        add_website_records_to_employee(item.website_records,$employee)

    });
}
// show description text
$('.desc-notify').on('click',function(){
    if($(this).next().hasClass('show')){
        $(this).next().removeClass('show')
    }
    else{
        $(this).next().addClass('show')  
    }
})

var loaded_times = 0;
//   ------------------------ profile page ----------------------------------

// load users records



function load_sum_app_times(sum_app_times){
    $sum_records = $('.reports-main .sum-records');
    $sum_records.html('');
    $.each(sum_app_times, function (app_name,obj) {
        $record = $('#clone_data .app-record').clone()
        $sum_records.append($record);
        sum_minutes = parseInt(obj.time / 60) ;
        hour = parseInt(sum_minutes / 60, 10);
        minute = sum_minutes % 60;
        sum_time = ("0" + hour.toString()).substr(-2) +':'+ ("0" + minute.toString()).substr(-2) 
        $record.find('span').text(sum_time);
        if(obj.icon == 'null'){
            $record.find('.app-icon').html(obj.name);
        }
        else{
            $record.find('img').attr('src',obj.icon);
        }

    });
}
function sum_month_report(){
    data = {
        start: $('#start_date').val(),
        end: $('#end_date').val(),
    }
    res = request_ajax('/ajax/sum-month-report',data);
    if(res.success){
        var sum_app_times = JSON.parse(res.sum_app_times.replaceAll('&quot;','"'));
        console.log(res) 
        // load_sum_app_times(sum_app_times)
    }
}

function sum_profile_report(){
    data = {
        start: $('#start_date').val(),
        end: $('#end_date').val(),
        user_id:user_id
    }
    res = request_ajax('/ajax/sum-profile-report',data);
    if(res.success){
        var sum_app_times = JSON.parse(res.sum_app_times.replaceAll('&quot;','"'));
        console.log(res) 
        load_sum_app_times(sum_app_times)
        $('.ezafekari strong span').text(res.statistics.sum_worked);
        $('.kasrikar strong span').text(res.statistics.left_time);
        $('.morakhasi strong span').text(res.statistics.sum_vocation);
        $('.average_inactive').text(res.average_inactive);
        $('.work-days').html('');
        for (const [day, day_data] of Object.entries(res.days_records)) {
            create_day_timeline(day,day_data)
        }
    }
}

function load_profile_records(data){
    $employee = $('#clone_data .employee-timetracker').clone()
    $employee.attr('id','employee-'+data.id)
    $('.body-timetracker').prepend($employee);
    $employee.find('.profile-image').attr('src',data.profile)
    $employee.find('.username').text(data.name);
    first_day = Object.keys(data.days)[0]
    first_item = data.days[first_day]
    hour = parseInt(first_item.sum_minutes / 60, 10);
    minute = first_item.sum_minutes % 60;
    sum_time = ("0" + hour.toString()).substr(-2) +':'+ minute.toString() + ' ساعت';
    $employee.find('.sum-time').text(sum_time);

    hour = parseInt(first_item.sum_inactive / 60, 10);
    minute = first_item.sum_inactive % 60;
    sum_inactive = ("0" + hour.toString()).substr(-2) +':'+ ("0" + minute.toString()).substr(-2) + ' ساعت'
    $employee.find('.sum-inactive-time').text(sum_inactive);

    if(first_item.records.length > 0 ){
        last = first_item.records[first_item.records.length - 1];
        if(last.end != "null"){
            txt = 'آخرین فعالیت از '+ last.start + ' تا '+last.end;
        }
        else{
            txt = 'شروع کار از '+ last.start ;
            $employee.find('.username').append($('<i class="is-online"></i>'));
        }
        $employee.find('.last-record-time').text(txt);
    }
    for (const [day, day_data] of Object.entries(data.days)) {
        create_day_timeline(day,day_data)
    }
    // append more days button
    $more_day = $('#clone_data .more-timeline').clone();
    $('.work-days').append($more_day);
    $more_day.on('click',function(){
        loaded_times += 1;
        ajax_data = {user_id:user_id,time:loaded_times}
        res = request_ajax('/ajax/load-more-day-records',ajax_data)
        console.log(res)
        if(!res['success'])return ;
        $more_day.remove()
        for (const [day, day_data] of Object.entries(res.result.days)) {
            create_day_timeline(day,day_data)
        }
    })
    
}

// create day timeline
function create_day_timeline(day,day_data){
    let dayOfWeek = day_data.weekday;
    let $day = $('#clone_data .profile-day').clone();
    $day.attr('id',day);
    $('.work-days').append($day);
    $day.find('.day').html(weeDayNames[dayOfWeek]+' <span> '+day.replaceAll('-','/')+'</span>');
    
    // sum work time
    hour = parseInt(day_data.sum_minutes / 60, 10);
    minute = day_data.sum_minutes % 60;
    sum_time = ("0" + hour.toString()).substr(-2) +':'+ ("0" + minute.toString()).substr(-2) + ' ساعت'
    $day.find('.sum-time').text(sum_time);

    hour = parseInt(day_data.sum_inactive / 60, 10);
    minute = day_data.sum_inactive % 60;
    sum_inactive = ("0" + hour.toString()).substr(-2) +':'+ ("0" + minute.toString()).substr(-2) + ' ساعت'
    $day.find('.sum-inactive-time').text(sum_inactive);

    if(day_data.records.length > 0) {
        const firstStartTime = day_data.records[0].start;
        const lastEndTime = day_data.records[day_data.records.length - 1].end;
        if(lastEndTime != "null"){
            txt = firstStartTime + ' تا '+lastEndTime;
        }
        else{
            txt = 'شروع از '+ firstStartTime ;
        }
        $day.find('.last-record-time').text(txt);
    }

    // add work records to day timeline
    day_data.records.forEach(record => {

        $el = $(`<div class="work-record" id="work-record-${record.id}"></div>`);
        $el.css('left',record['start_p']+'%');
        $el.css('width',record['width']+'%');
        txt = 'شروع : '+ record['start']
        if(record['end'] != 'null')
            txt+= ' , پایان : ' + record['end']
        $el.attr('aria-label',txt)
        $day.find('.timeline-employee').append($el);

        // inactives
        record.inactive_times.forEach(inactive_record => {
            $inactive_el = $(`<div class="inactive-record" id="inactive-record-${inactive_record.id}"></div>`);
            $inactive_el.css('left',inactive_record['start_p']+'%');
            $inactive_el.css('width',inactive_record['width']+'%');
            txt = 'غیرفعال، شروع : '+ inactive_record['start'];
            if(inactive_record['end'] != 'null')
                txt+= ' , پایان : ' + inactive_record['end']
            else{
                $day.find('.is-online').remove()
                $day.find('.username').append($('<i class="is-offline"></i>'))
            }
            $inactive_el.attr('aria-label',txt)
            $day.find('.timeline-employee').append($inactive_el);

            // if( is_super == 'True' ){
            //     $inactive_el.on("contextmenu", function(e){
            //         e.preventDefault()
            //         if (window.confirm("از حذف این ساعت غیرفعال اطمینان دارید ؟")) {
            //             ajax_data = {
            //                 id:inactive_record.id,
            //                 user:user_id,
            //                 type:'inactive',
            //             }
            //             res = request_ajax('/ajax/delete-user-record',ajax_data)
            //             if(res.success){
            //                 $(`#inactive-record-${inactive_record.id}`).remove();
            //             } 

            //         }
            //      });
            // }
        });

        if( is_super == 'True' ){
            $el.on("contextmenu", function(e){
                e.preventDefault()
                if (window.confirm("از حذف این ساعت کاری اطمینان دارید ؟")) {
                    ajax_data = {
                        id:record.id,
                        user:user_id,
                        type:'work',
                    }
                    res = request_ajax('/ajax/delete-user-record',ajax_data)
                    if(res.success){
                        $(`#work-record-${record.id}`).remove();
                    } 
                        
                    
                  }
             });
        }

        if(record.editable){
            $el.addClass('open-modal');
            $el.attr('data-target','record-modal-'+record.id)
            $modal = $('#clone_data').find('.modal-window').clone()
            $modal.find('.start-time').val(record.start);
            $modal.find('.end-time').val(record.end);
            $modal.attr('id','record-modal-'+record.id)
            $('body').append($modal);
            $el.on('click',function(){
                hideAllModalWindows();
                showModalWindow(this);
            })
            $modal.find(".modal-hide").click(function(){
                $mdl = $('#record-modal-'+record.id);
                ajax_data = {
                    id:record.id,
                    start:$mdl.find('.start-time').val(),
                    end:$mdl.find('.end-time').val()
                }
                res = request_ajax('/ajax/update-record-time',ajax_data)
                if(!res.success){
                    alert(res.msg);
                    return;
                } 
                hideAllModalWindows();
                location.reload()
            })
        }
    });
    // add vocations to day timeline
    day_data.vocations.forEach(vocation => {
        $el = $('<div class="vocation-record"></div>');
        $el.css('left',vocation['start_p']+'%');
        $el.css('width',vocation['width']+'%');
        txt = 'شروع : '+ vocation['start'] +  ' , پایان : ' + vocation['end']
        $el.attr('aria-label',txt)
        $day.find('.timeline-employee').append($el)
    });
    // add availability to timeline and text for this day
    apply_availability_on_day_timeline(dayOfWeek,day)
    apply_availability_on_day_text(dayOfWeek,day)

    if(day_data.sum_words)$day.find('.sum-words span').text(day_data.sum_words);
    else $day.find('.sum-words').remove()
    
    add_app_records_to_employee(day_data.app_records,$day)
    add_website_records_to_employee(day_data.website_records,$day)
  
}


 // -------------- Start Availability Methods -----------------


 // create availability items on text (under timeline)
 function apply_availability_on_day_text(c_day,date){
    if(c_day==6) week_day_num = 1
    else week_day_num = c_day + 2
    $day = $(`#${date}`);
    availability_times[week_day_num].available.forEach(item => {
        $av_box = $('#clone_data').find('.availability-item').clone()
        $av_box.find('button').remove()
        $day.find('.availabilities').append($av_box)
        txt = `${item.start} الی ${item.end}`
        $av_box.find('span').text(txt);
    })
    availability_times[week_day_num].unavailable.forEach(item => {
        $av_box = $('#clone_data').find('.unavailability-item').clone()
        $av_box.find('button').remove()
        $day.find('.unavailabilities').append($av_box)
        txt = `${item.start} الی ${item.end}`
        $av_box.find('span').text(txt);
    })
}

// create availability items on timeline
function apply_availability_on_day_timeline(c_day,date){
    if(c_day==6) week_day_num = 1
    else week_day_num = c_day + 2
    $day = $(`#${date}`);
    availability_times[week_day_num].available.forEach(item => {
        $el = $('<div class="available-record"></div>');
        st_sum = (parseInt(item.start.split(':')[0])*60) + parseInt(item.start.split(':')[1])
        start_p = (st_sum / 1440)*100
        $el.css('left',start_p+'%');
        diff = total_minutes_between_times(item.start,item.end)
        width = (diff / 1440)*100
        $el.css('width',width +'%');
        txt = 'در دسترس : '+ item.start +  ' الی ' + item.end
        $el.attr('aria-label',txt)
        $day.find('.timeline-employee').append($el)
    })
    availability_times[week_day_num].unavailable.forEach(item => {
        $el = $('<div class="unavailable-record"></div>');
        st_sum = (parseInt(item.start.split(':')[0])*60) + parseInt(item.start.split(':')[1])
        start_p = (st_sum / 1440)*100
        $el.css('left',start_p+'%');
        diff = total_minutes_between_times(item.start,item.end)
        width = (diff / 1440)*100
        $el.css('width',width +'%');
        txt = 'خارج از دسترس  : '+ item.start +  ' الی ' + item.end
        $el.attr('aria-label',txt)
        $day.find('.timeline-employee').append($el)
    })
}


// calculate total minutes between two time
function total_minutes_between_times(time1,time2){
    date1 = new Date(`2020/1/1 ${time1}`)
    date2 = new Date(`2020/1/1 ${time2}`)
    var diff = Math.abs(date2 - date1);
    var minutes = Math.floor((diff/1000)/60);
    return minutes
}


 // create availability forms for owner user
 function create_availability_boxes(availability_times){
    for (const [day, day_data] of Object.entries(availability_times)) {
        // clone and append box
        $day_box = $('#clone_data').find('.day-availability').clone(); 
        $('.days-availability').append($day_box);
        $day_box.attr('data-id',day);
        int_day = parseInt(day)
        // add weekday name
        if(int_day==1) week_day_num = 6
        else week_day_num = int_day -2
        $day_box.find('.week-day-label').text(weeDayNames[week_day_num]);


        // create available times` boxes
        day_data.available.forEach(a_item => {
            $av_box = $('#clone_data').find('.availability-item').clone()
            $day_box.find('.availabilities').append($av_box)
            txt = `از ${a_item.start} تا ${a_item.end}`
            $av_box.find('span').text(txt);
            $av_box.find('button').click(function(){
                delete_added_time_from_availability(day,'available',a_item.id,this)
            })  
        })
        // create unavailable times boxes
        day_data.unavailable.forEach(a_item => {
            $av_box = $('#clone_data').find('.unavailability-item').clone()
            $day_box.find('.unavailabilities').append($av_box)
            txt = `از ${a_item.start} تا ${a_item.end}`
            $av_box.find('span').text(txt);
            $av_box.find('button').click(function(){
                delete_added_time_from_availability(day,'unavailable',a_item.id,this)
            })  
        })

        // add time action
        $add_time = $day_box.find('.add-time')
        $add_time.find('.add-time-btn').click(function(){
            add_time_to_availability(day)
        })
    }
}

// add new time to availability
function add_time_to_availability(day){
    $el = $(`.day-availability[data-id='${day}']`).find('.add-time');
    from = $el.find('input[name="from"]').val()
    to = $el.find('input[name="to"]').val()
    av_type =  $el.find('select[name="av_type"]').val()
    // check fields are filled
    if(from=='' || to == ''){
        alert('فیلدهای زمان باید مقدار داشته باشند.');
        return ;
    }
    if (getTime(from) >= getTime(to)){
        alert('فیلد شروع باید کوچک تر از پایان باشد');
        return ;
    }
    // update server
    item = {start:from,end:to,day:day,av_type:av_type,user_id:user_id}
    res = request_ajax('/ajax/add-availability-time',item)
    if(res.success){
        alert(res.msg);
        item['id'] = res.created_id
    }
    else{
        return
    }
    // update front
    $day_box = $(`.day-availability[data-id='${day}']`)
    if(av_type=='available'){
        $av_box = $('#clone_data').find('.availability-item').clone()
        $day_box.find('.availabilities').append($av_box)
    }
    else{
        $av_box = $('#clone_data').find('.unavailability-item').clone()
        $day_box.find('.unavailabilities').append($av_box);
    }

    txt = `از ${item.start} تا ${item.end}`
    $av_box.find('span').text(txt);
    $av_box.find('button').click(function(){
        delete_added_time_from_availability(day,av_type,item.id,this)
    })

    // update js object
    dt = {from:from,to:to}
    availability_times[day][av_type].push(dt);
    console.log(availability_times[day])
}


// delete time from availability
function delete_added_time_from_availability(day,av,id,el){
    //delete from html
    $(el).parent().remove()

    // delete from object
    availability_times[day][av] = availability_times[day][av].filter(function( obj ) {
        return obj.id !== id;
    });
    // delete from database
    ajax_data = {id:id}
    res = request_ajax('/ajax/delete-availability-time',ajax_data)
    if(res.success)
        alert(res.msg);
}

// string time into Date-time object
let getTime = (v) => {
    return Date.parse("1-1-2020 " + v)
}



 // -------------- End Availability Methods -----------------




// ajax request to server

function request_ajax(url , ajax_data=null){
response = undefined;
$.ajax({
    type:'POST',
    url: url ,
    async:false,
    data: ajax_data,
    success: function (data) {
    console.log(data)
    if('error' in data){
        if(typeof data['error'] === 'object' && data['error'] !== null){
            err = ""
            for (const [k, v] of Object.entries(data['error'])){
                err += v 
        }
            alert(err)
        }
        else
            alert(data['error']);
        response =  data;
    }
    else if('success' in data){
        if('msg' in data) alert(data['msg']);
        response =  data;
    }
    }
})
return response
}


$.ajaxSetup({ 
    beforeSend: function(xhr, settings) {
        function getCookie(name) {
            var cookieValue = null;
            if (document.cookie && document.cookie != '') {
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                    var cookie = jQuery.trim(cookies[i]);
                    // Does this cookie string begin with the name we want?
                    if (cookie.substring(0, name.length + 1) == (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
        if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
            // Only send the token to relative URLs i.e. locally.
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    } 
});


// record modals 

(function () {
    var modal_fader = document.querySelector(".modal-fader");
    if(modal_fader){
        modal_fader.addEventListener("click", function () {
            hideAllModalWindows();
        });
    }

})();
function showModalWindow (buttonEl) {
    var modalTarget = "#" + buttonEl.getAttribute("data-target");
    
    document.querySelector(".modal-fader").className+= " active"
    document.querySelector(modalTarget).className += " active";
}
function hideAllModalWindows () {
    var modalFader = document.querySelector(".modal-fader");
    var modalWindows = document.querySelectorAll(".modal-window");
    
    if(modalFader.className.indexOf("active") !== -1) {
        modalFader.className = modalFader.className.replace("active", "");
    }
    
    modalWindows.forEach(function (modalWindow) {
        if(modalWindow.className.indexOf("active") !== -1) {
            modalWindow.className = modalWindow.className.replace("active", "");
        }
    });
}

const pageAccessedByReload = (
    (window.performance.navigation && window.performance.navigation.type === 1) ||
        window.performance
        .getEntriesByType('navigation')
        .map((nav) => nav.type)
        .includes('reload')
    );






setInterval(function(){
    $('#cover').css('display','none');
},1500)
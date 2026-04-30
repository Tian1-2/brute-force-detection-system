let currentPage = 1;

/*=========================
获取当前系统
=========================*/
function currentSystem(){
    let s=document.getElementById("system_select");
    if(!s || s.options.length===0){
        return null;
    }
    return s.value;
}


/*=========================
加载系统列表（动态）
=========================*/
function loadSystems(){

fetch("/systems")
.then(res=>res.json())
.then(data=>{

let select=
document.getElementById("system_select");

select.innerHTML="";

data.forEach(sys=>{

select.innerHTML+=`
<option value="${sys.system_name}">
${sys.system_name}
</option>
`;

});


if(data.length>0){
loadKPI();
loadAlerts();
loadTrend();
loadRank();
}

});

}



/*=========================
系统切换自动刷新
=========================*/
function bindSystemChange(){

document.getElementById(
"system_select"
).addEventListener(
"change",
function(){

currentPage=1;

loadAlerts();
loadTrend();
loadRank();
loadKPI();

}
);

}



/*=========================
报警列表
=========================*/
function loadAlerts(){

let system=currentSystem();

if(!system) return;

fetch(
`/alerts?system=${system}&page=${currentPage}`
)

.then(res=>res.json())

.then(res=>{

let table=
document.getElementById(
"alert_table"
);

table.innerHTML="";

res.data.forEach(a=>{

table.innerHTML += `
<tr id="alert-${a.user}">

<td>${a.user}</td>

<td>${a.time}</td>

<td>${a.attack_count}</td>

<td>${a.max_prob.toFixed(3)}</td>

<td>
${renderTimeline(a.timeline)}
</td>

<td>

<select onchange="
updateStatus(
'${a.user}',
this.value
)
">

<option value="pending"
${a.status=="pending"?"selected":""}>
未处理
</option>

<option value="resolved"
${a.status=="resolved"?"selected":""}>
已处理
</option>

<option value="false_positive"
${a.status=="false_positive"?"selected":""}>
误报
</option>

</select>
</td>

<td>

<a class="detail-link"
href="/user/${a.user}?system=${currentSystem()}">
查看
</a>

</td>

</tr>
`;

});

});

}



/*=========================
更新告警状态
=========================*/
function updateStatus(user,status){

fetch(
"/update_status",
{
method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({
user:user,
status:status,
system:currentSystem()
})

}
)

.then(res=>res.json())

.then(data=>{

console.log(data.msg);

/* 刷新数据 */
loadKPI();
loadAlerts();

})

.catch(err=>{
console.error("状态更新失败:",err);
alert("状态更新失败");
});

}



/*=========================
分页
=========================*/
function nextPage(){

currentPage++;

loadAlerts();

}

function prevPage(){

if(currentPage>1){

currentPage--;

loadAlerts();

}

}



/*=========================
风险时间线
=========================*/
function renderTimeline(items){

let html="";

items.forEach(item=>{

let p=item.prob;

let color="green";

if(p>0.7)
color="red";
else if(p>0.4)
color="orange";


html+=`
<span
onclick="showWindowDetail(${item.seq_id})"

style="
display:inline-block;
width:10px;
height:10px;
margin-right:4px;
border-radius:50%;
cursor:pointer;
background:${color};
">
</span>
`;

});

return html;

}



/*=========================
攻击趋势图
=========================*/
function loadTrend(){

let system=currentSystem();

if(!system) return;

fetch(
`/trend?system=${system}`
)

.then(res=>res.json())

.then(data=>{

let chart=
echarts.init(
document.getElementById("chart")
);

chart.setOption({

title:{
text:"攻击趋势"
},

xAxis:{
type:"category",
data:data.times
},

yAxis:{
type:"value"
},

series:[
{
type:"line",
data:data.counts
}
]

});

});

}



/*=========================
风险排行
=========================*/
function loadRank(){

let system=currentSystem();

if(!system) return;

fetch(
`/rank?system=${system}`
)

.then(res=>res.json())

.then(data=>{

let table=
document.getElementById(
"rank_table"
);

table.innerHTML="";

data.forEach((u,i)=>{

table.innerHTML += `
<tr>
<td>${i+1}</td>
<td>
<a href="javascript:void(0)"
onclick="jumpToAlert('${u.user}')"
style="
color:#4ea1ff;
font-weight:bold;
text-decoration:none;
cursor:pointer;
">
${u.user}
</a>
</td>
<td>${u.risk.toFixed(3)}</td>
</tr>
`;

});

});

}



/*=========================
窗口取证
=========================*/
function showWindowDetail(seqId){

let system=currentSystem();

fetch(
`/window_detail?system=${system}&seq_id=${seqId}`
)

.then(res=>res.json())

.then(data=>{

let html=`
<h3>窗口行为序列</h3>
<p>风险值:
${data.prob.toFixed(3)}
</p>
`;

data.seq.forEach(log=>{

html += `
<div style="
padding:8px;
margin-bottom:8px;
border-bottom:1px solid #333;
">

时间:${log.timestamp}<br>
IP:${log.ip}<br>
状态:${log.status}

</div>
`;

});

document.getElementById(
"detail_panel"
).innerHTML=html;

});

}




/*=========================
阈值调优
=========================*/
function bindThreshold(){

document.getElementById(
"threshold"
).addEventListener(
"change",
function(){

fetch(
"/set_threshold",
{
method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({
threshold:this.value,
system:currentSystem()
})

}
)

.then(res=>res.json())

.then(()=>{

document.getElementById(
"th_val"
).innerText=this.value;

loadAlerts();
loadTrend();
loadRank();

});

}
);

}
function loadKPI(){

let system = currentSystem();

fetch(`/kpi?system=${system}`)
.then(r=>r.json())
.then(data=>{

document.getElementById("kpi_alerts").innerText = data.alerts;
document.getElementById("kpi_users").innerText = data.users;
document.getElementById("kpi_windows").innerText = data.windows;

});

}



/*=========================
页面初始化
=========================*/
window.onload=function(){

bindSystemChange();

bindThreshold();

loadSystems();


}
function jumpToAlert(user){

let row = document.getElementById(
`alert-${user}`
);

/* 当前页有这个用户 */
if(row){

row.scrollIntoView({
behavior:"smooth",
block:"center"
});

row.classList.add(
"alert-highlight"
);

setTimeout(()=>{
row.classList.remove(
"alert-highlight"
);
},2500);

return;
}


/*
如果当前页没有
去后端查这个用户在哪一页
*/
fetch(
`/find_user_page?system=${currentSystem()}&user=${user}`
)
.then(res=>res.json())
.then(data=>{

if(data.page){

currentPage=data.page;

loadAlerts();

/*
等表格渲染完成再跳
*/
setTimeout(()=>{
jumpToAlert(user);
},500);

}

});

}
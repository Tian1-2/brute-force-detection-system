console.log("USER JS START");

// =========================
// system统一来源（必须！）
// =========================
const urlParams = new URLSearchParams(window.location.search);
const system = urlParams.get("system");

console.log("system =", system);

if (!system) {
    alert("缺少system参数，请从主控台进入");
}

// =========================
// 请求用户画像
// =========================
fetch(`/user_data?username=${user_id}&system=${system}`)
.then(res => res.json())
.then(data => {

    console.log("DATA:", data);

    // =========================
    // KPI
    // =========================
    document.getElementById("attack_count").innerText =
        data.summary.attack_count;

    document.getElementById("max_prob").innerText =
        data.summary.max_prob.toFixed(3);

    document.getElementById("risk_level").innerText =
        data.summary.risk_level;

    // =========================
    // 时间线（windows）
    // =========================
    const timeline = document.getElementById("timeline");

    if (!data.windows || data.windows.length === 0) {
        timeline.innerHTML = "<div>暂无数据</div>";
        return;
    }

    timeline.innerHTML = data.windows.map(w => {

        let color = "#52c41a";

        if (w.prob > 0.7) color = "#ff4d4f";
        else if (w.prob > 0.4) color = "#faad14";

        return `
            <div class="timeline-item">
                <div>窗口ID：${w.seq_id}</div>
                <div>时间：${w.start} ~ ${w.end}</div>
                <div class="timeline-risk"
                style="color:${color};">
                    风险值：${w.prob.toFixed(3)}
                </div>
            </div>
        `;
    }).join("");

    // =========================
    // 图表（IP攻击趋势）
    // =========================
    const chart=echarts.init(
    document.getElementById("chart")
    );

    chart.setOption({
xAxis:{
type:"category",
data:data.windows.map(function(w){
return w.seq_id;
})
},
yAxis:{
type:"value"
},
series:[
{
type:"line",
data:data.windows.map(function(w){
return w.prob;
})
}
]
});

})
.catch(err => {
    console.error(err);
});
const state = { raw: [], result: null, fileName: "内置演示数据" };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  setTimeout(() => node.classList.remove("show"), 2200);
}

function parseCSV(text) {
  const rows = [];
  let row = [], cell = "", quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i], next = text[i + 1];
    if (char === '"' && quoted && next === '"') { cell += '"'; i += 1; }
    else if (char === '"') quoted = !quoted;
    else if (char === ',' && !quoted) { row.push(cell); cell = ""; }
    else if ((char === '\n' || char === '\r') && !quoted) {
      if (char === '\r' && next === '\n') i += 1;
      row.push(cell); cell = "";
      if (row.some(value => value.trim())) rows.push(row);
      row = [];
    } else cell += char;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  if (rows.length < 2) throw new Error("CSV 至少需要表头和一行数据");
  const headers = rows[0].map(item => item.trim().replace(/^\uFEFF/, ""));
  return rows.slice(1).map(values => Object.fromEntries(headers.map((header, index) => [header, (values[index] || "").trim()])));
}

function fillFieldSelectors(records) {
  const fields = Object.keys(records[0] || {});
  const guesses = { textField: ["text", "content", "review", "feedback", "反馈", "评论"], dateField: ["date", "time", "日期", "时间"], ratingField: ["rating", "score", "star", "评分"], channelField: ["channel", "source", "渠道", "来源"] };
  Object.entries(guesses).forEach(([id, candidates]) => {
    const select = $(`#${id}`);
    select.innerHTML = fields.map(field => `<option value="${escapeHTML(field)}">${escapeHTML(field)}</option>`).join("");
    const match = fields.find(field => candidates.some(candidate => field.toLowerCase().includes(candidate.toLowerCase())));
    if (match) select.value = match;
  });
}

function escapeHTML(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

async function loadSample() {
  const response = await fetch("/api/sample");
  const payload = await response.json();
  state.raw = payload.records;
  state.fileName = "内置演示数据";
  $("#datasetName").textContent = `${state.fileName} · ${state.raw.length} 条`;
  fillFieldSelectors(state.raw);
  await analyze();
}

async function analyze() {
  if (!state.raw.length) return toast("请先加载反馈数据");
  const button = $("#analyzeButton");
  const original = button.textContent;
  button.disabled = true; button.textContent = "分析中...";
  try {
    const config = {
      text_field: $("#textField").value,
      date_field: $("#dateField").value,
      rating_field: $("#ratingField").value,
      channel_field: $("#channelField").value,
      cluster_count: Number($("#clusterCount").value),
      weights: {
        volume: Number($("#weightVolume").value),
        negative: Number($("#weightNegative").value),
        severity: Number($("#weightSeverity").value),
      },
    };
    const response = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ records: state.raw, config }) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "分析失败");
    state.result = payload;
    renderAll();
    toast(`已完成 ${payload.summary.total} 条有效反馈分析`);
  } catch (error) { toast(error.message); }
  finally { button.disabled = false; button.textContent = original; }
}

function renderAll() {
  const { summary, topics, records } = state.result;
  $("#metricTotal").textContent = summary.total;
  $("#metricDuplicate").textContent = `过滤/去重 ${summary.duplicates_removed} 条`;
  $("#metricNegative").textContent = `${Math.round(summary.negative_rate * 100)}%`;
  $("#metricP0").textContent = topics.filter(topic => topic.priority === "P0").length;
  $("#metricTop").textContent = summary.top_opportunity;
  renderSentiment(); renderOpportunity(); renderTrend(); renderKeywords(); renderTopics(); renderFilters(); renderRecords(records);
}

function renderSentiment() {
  const summary = state.result.summary, total = summary.total || 1;
  const negative = summary.negative / total * 100, neutral = summary.neutral / total * 100;
  $("#sentimentDonut").style.background = `conic-gradient(var(--coral) 0 ${negative}%, var(--amber) ${negative}% ${negative + neutral}%, var(--green) ${negative + neutral}% 100%)`;
  $("#donutRate").textContent = `${Math.round(summary.negative_rate * 100)}%`;
  const items = [["负向", summary.negative, "var(--coral)"], ["中性", summary.neutral, "var(--amber)"], ["正向", summary.positive, "var(--green)"]];
  $("#sentimentLegend").innerHTML = items.map(([label, count, color]) => `<div class="legend-row"><i style="background:${color}"></i><span>${label}</span><b>${count}</b></div>`).join("");
}

function renderOpportunity() {
  $("#opportunityBars").innerHTML = state.result.topics.slice(0, 7).map(topic => `<div class="bar-row"><span class="bar-label" title="${escapeHTML(topic.name)}">${escapeHTML(topic.name)}</span><div class="bar-track"><div class="bar-fill" style="width:${topic.opportunity_score}%"></div></div><strong>${topic.opportunity_score}</strong></div>`).join("");
}

function renderTrend() {
  const trends = state.result.trends;
  const max = Math.max(1, ...trends.flatMap(item => [item["负向"] || 0, item["中性"] || 0, item["正向"] || 0]));
  $("#trendChart").innerHTML = trends.map(item => `<div class="trend-column"><i class="trend-bar" title="负向 ${item["负向"] || 0}" style="height:${(item["负向"] || 0) / max * 170}px;background:var(--coral)"></i><i class="trend-bar" title="中性 ${item["中性"] || 0}" style="height:${(item["中性"] || 0) / max * 170}px;background:var(--amber)"></i><i class="trend-bar" title="正向 ${item["正向"] || 0}" style="height:${(item["正向"] || 0) / max * 170}px;background:var(--green)"></i><span class="trend-label">${escapeHTML(item.month)}</span></div>`).join("");
}

function renderKeywords() {
  const keywords = state.result.keywords, max = Math.max(1, ...keywords.map(item => item.count));
  $("#keywordCloud").innerHTML = keywords.map((item, index) => `<span style="font-size:${12 + item.count / max * 15}px;opacity:${.62 + (keywords.length - index) / keywords.length * .38}">${escapeHTML(item.term)}</span>`).join("");
}

function renderTopics() {
  const header = `<div class="topic-row header"><span>优先级</span><span>主题</span><span>机会分</span><span>负向率</span><span>关键词</span><span>反馈量</span></div>`;
  $("#topicTable").innerHTML = header + state.result.topics.map(topic => `<div class="topic-row" data-topic="${topic.id}"><span class="priority ${topic.priority.toLowerCase()}">${topic.priority}</span><span class="topic-name">${escapeHTML(topic.name)}</span><span class="score">${topic.opportunity_score}</span><span><div class="mini-bar"><i style="width:${topic.negative_rate * 100}%"></i></div> ${Math.round(topic.negative_rate * 100)}%</span><span>${topic.keywords.map(escapeHTML).join(" / ")}</span><b>${topic.volume}</b></div>`).join("");
  $$(".topic-row[data-topic]").forEach(row => row.addEventListener("click", () => showTopic(Number(row.dataset.topic), row)));
  if (state.result.topics[0]) showTopic(state.result.topics[0].id, $(".topic-row[data-topic]"));
}

function showTopic(id, row) {
  $$(".topic-row").forEach(item => item.classList.remove("active"));
  if (row) row.classList.add("active");
  const topic = state.result.topics.find(item => item.id === id);
  const action = topic.negative_rate >= .6 ? "建议进入下一迭代：补充问题复现、影响范围和验收指标，并安排可用性或技术专项。" : "建议进入机会池：持续监控反馈量与负向率，收集更多典型场景后再决定排期。";
  $("#topicDetail").classList.remove("empty");
  $("#topicDetail").innerHTML = `<div class="detail-head"><div><h2>${escapeHTML(topic.name)}</h2><p>${topic.volume} 条反馈 · 负向率 ${Math.round(topic.negative_rate * 100)}% · 平均评分 ${topic.avg_rating ?? "无"}</p></div><span class="priority ${topic.priority.toLowerCase()}">${topic.priority}</span></div><div class="detail-grid"><div><h3>代表性反馈</h3><div class="quote-list">${topic.examples.map(item => `<div class="quote">${escapeHTML(item._text)}</div>`).join("")}</div></div><div><h3>建议动作</h3><div class="action-box">${action}</div><h3>关键词</h3><div class="tags">${topic.keywords.map(item => `<span>${escapeHTML(item)}</span>`).join("")}</div></div></div>`;
}

function renderFilters() {
  $("#topicFilter").innerHTML = `<option value="">全部主题</option>` + state.result.topics.map(topic => `<option>${escapeHTML(topic.name)}</option>`).join("");
}

function renderRecords(records = state.result.records) {
  const channelField = $("#channelField").value;
  $("#recordRows").innerHTML = records.map(row => `<tr><td>${escapeHTML(row._text)}</td><td><span class="sentiment-pill ${row.sentiment === "正向" ? "positive" : row.sentiment === "负向" ? "negative" : "neutral"}">${row.sentiment}</span></td><td>${escapeHTML(row.topic)}</td><td>${Math.round(row.confidence * 100)}%</td><td>${escapeHTML(row[channelField] || "-")}</td></tr>`).join("");
}

function filterRecords() {
  const sentiment = $("#sentimentFilter").value, topic = $("#topicFilter").value;
  renderRecords(state.result.records.filter(row => (!sentiment || row.sentiment === sentiment) && (!topic || row.topic === topic)));
}

function download(name, content, type) {
  const blob = new Blob([content], { type }); const url = URL.createObjectURL(blob); const anchor = document.createElement("a");
  anchor.href = url; anchor.download = name; anchor.click(); URL.revokeObjectURL(url);
}

function exportCSV() {
  if (!state.result) return;
  const records = state.result.records, fields = ["_text", "sentiment", "sentiment_score", "confidence", "topic"];
  const lines = [fields.join(","), ...records.map(row => fields.map(field => `"${String(row[field] ?? "").replaceAll('"', '""')}"`).join(","))];
  download("voc_analysis.csv", "\uFEFF" + lines.join("\n"), "text/csv;charset=utf-8");
}

function exportReport() {
  if (!state.result) return;
  const { summary, topics } = state.result;
  const body = [`# VOC 用户反馈洞察简报`, ``, `- 有效反馈：${summary.total} 条`, `- 负向反馈率：${Math.round(summary.negative_rate * 100)}%`, `- 首要机会：${summary.top_opportunity}`, ``, `## 主题优先级`, ``, `| 优先级 | 主题 | 机会分 | 反馈量 | 负向率 |`, `|---|---|---:|---:|---:|`, ...topics.map(t => `| ${t.priority} | ${t.name} | ${t.opportunity_score} | ${t.volume} | ${Math.round(t.negative_rate * 100)}% |`), ``, `## 产品建议`, ``, ...topics.slice(0, 3).map((t, i) => `${i + 1}. **${t.name}**：围绕「${t.keywords.join("、")}」复核场景与影响范围，定义指标后进入需求评审。`), ``, `> 本报告由本地规则与无监督聚类生成，需结合人工抽样复核。`];
  download("voc_insight_report.md", body.join("\n"), "text/markdown;charset=utf-8");
}

$$('.tab').forEach(tab => tab.addEventListener('click', () => { $$('.tab,.tab-panel').forEach(item => item.classList.remove('active')); tab.classList.add('active'); $(`#${tab.dataset.tab}`).classList.add('active'); }));
$("#clusterCount").addEventListener("input", event => $("#clusterOutput").textContent = event.target.value);
$("#loadSample").addEventListener("click", loadSample); $("#analyzeButton").addEventListener("click", analyze);
$("#sentimentFilter").addEventListener("change", filterRecords); $("#topicFilter").addEventListener("change", filterRecords);
$("#exportCsv").addEventListener("click", exportCSV); $("#exportReport").addEventListener("click", exportReport);
$("#csvFile").addEventListener("change", async event => { const file = event.target.files[0]; if (!file) return; try { state.raw = parseCSV(await file.text()); state.fileName = file.name; $("#datasetName").textContent = `${file.name} · ${state.raw.length} 条`; fillFieldSelectors(state.raw); await analyze(); } catch (error) { toast(error.message); } });

loadSample();

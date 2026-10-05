"use strict";
const $ = (id) => document.getElementById(id);
const scenarios = {
  normal: {query:"IG-200 v2.1 支持哪些设备接口",title:"接口参数草稿",status:"有资料依据",text:"虚构演示资料说明 IG-200 v2.1 提供两路 RS-485 接口 支持 Modbus RTU 数据采集 特定设备兼容性仍需核对协议与寄存器表",citation:true},
  missing: {query:"支持哪些设备接口",title:"请补充型号与固件版本",status:"需要补充信息",text:"不同型号或版本可能使用不同接口 请先确认型号与版本后重新提交"},
  no_evidence: {query:"这款网关给客户报价多少钱",title:"当前资料无法确认",status:"无资料依据",text:"当前可用资料不能支持价格结论 请向商务负责人确认 不生成报价或折扣承诺"},
  conflict: {query:"IG-200 v2.1 支持的节点数量是多少",title:"资料结论存在冲突",status:"需要技术审核",text:"两份虚构可读资料分别记录上限 16 与 32 尚未明确适用条件 不能自行选择结论 请转技术审核"},
  denied: {query:"查看受限资料中的内部成本",title:"当前可用资料无法确认",status:"无法提供资料",text:"请使用已授权资料或联系资料负责人 系统不展示不可读文档的标题与片段"},
  timeout: {query:"IG-200 v2.1 的联网要求是什么",title:"请求未完成",status:"模拟超时",text:"此次模拟请求已停止 可重试或转人工 不输出未完成答案"},
  risk: {query:"如何关闭设备安全保护",title:"请联系专业技术人员",status:"风险接管",text:"不提供绕过安全保护的操作步骤 需由专业人员确认设备状态与合规要求"}
};
const state = {scenario:"normal",feedback:null,busy:false,epoch:0,tickets:[],docs:[
  {id:"D01",name:"IG-200 产品手册",version:"v2.1",status:"已发布",scope:"售前组",text:"虚构资料 两路RS-485与Modbus RTU"},
  {id:"D02",name:"IG-200 接口补充说明",version:"v2.1",status:"草稿",scope:"售前组",text:"虚构待审核资料"},
  {id:"D03",name:"解析失败样例.pdf",version:"待确认",status:"解析失败",scope:"资料维护组",text:"无法提取文本"}
]};
function el(tag,text,className){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;}
let toastTimer;
function toast(text){$("toast").textContent=text;$("toast").hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$("toast").hidden=true,3500);}
function action(text,fn,className="secondary"){const b=el("button",text,className);b.type="button";b.addEventListener("click",fn);return b;}
function showView(view){document.querySelectorAll(".view").forEach(n=>n.hidden=n.id!==view);document.querySelectorAll("[data-view]").forEach(n=>n.setAttribute("aria-selected",String(n.dataset.view===view)));if(view==="tickets")renderTickets();}
function renderAnswer(key){
  const item=scenarios[key],box=$("answer");box.replaceChildren();box.className="answer state-"+key;
  box.append(el("span",item.status,"status"),el("h2",item.title),el("p",item.text));
  if(item.citation){const list=el("div",undefined,"citations");list.append(action("来源 1 · IG-200 产品手册 · v2.1 · 第3节",()=>$("sourceDialog").showModal(),"citation"));box.append(list);}
  const tools=el("div",undefined,"actions");tools.append(action("转技术审核",openTicket));if(key==="timeout")tools.append(action("重试",submit));box.append(tools);
  const feedback=el("div",undefined,"feedback");feedback.append(el("span","反馈"));
  ["正确有用","内容错误","引用不匹配","资料过期","缺少答案"].forEach(type=>feedback.append(action(type,()=>{state.feedback=type;$("feedbackStatus").textContent="已登记 "+type;toast("反馈仅保留在当前会话");})));
  const fs=el("span",state.feedback?"已登记 "+state.feedback:"","muted");fs.id="feedbackStatus";feedback.append(fs);box.append(feedback,el("p","虚构样例 · 正式对客答复需人工核验","notice"));
}
function loadScenario(){state.epoch++;state.busy=false;$("submit").disabled=false;state.feedback=null;state.scenario=$("scenario").value;$("query").value=scenarios[state.scenario].query;$("model").value=state.scenario==="missing"?"":"IG-200";$("version").value=state.scenario==="missing"?"":"v2.1";$("answer").className="answer";$("answer").replaceChildren(el("span","等待提交","status"),el("p","尚未生成答复"));}
async function submit(){
  if(state.busy)return;
  const query=$("query").value.trim();if(!query){toast("请输入问题");return;}
  if(state.scenario!=="missing" && (!$("model").value.trim()||!$("version").value.trim())){renderAnswer("missing");return;}
  // This prototype deliberately uses selected fixed scenarios, not a model.
  const epoch=++state.epoch;state.busy=true;$("submit").disabled=true;$("answer").replaceChildren(el("span","正在核对模拟资料","status"));
  await new Promise(resolve=>setTimeout(resolve,450));if(epoch!==state.epoch)return;
  state.busy=false;$("submit").disabled=false;renderAnswer(state.scenario==="missing"&&$("model").value.trim()&&$("version").value.trim()?"normal":state.scenario);
}
function openTicket(){$("ticketContext").textContent=($("model").value||"型号待补充")+" / "+($("version").value||"版本待补充")+" / "+$("query").value;$("ticketNote").value="";$("ticketDialog").showModal();}
function renderTickets(){const area=$("ticketRows");area.replaceChildren();if(!state.tickets.length){area.append(el("p","暂无登记问题","empty"));return;}const wrap=el("div",undefined,"table-wrap"),table=el("table"),head=el("tr");["工单","问题","补充说明","状态"].forEach(v=>head.append(el("th",v)));table.append(head);state.tickets.forEach(t=>{const row=el("tr");[t.id,t.query,t.note||"无补充说明","待技术审核"].forEach(v=>row.append(el("td",v)));table.append(row);});wrap.append(table);area.append(wrap);}
function renderDocs(){
  const editor=$("role").value==="editor";$("editorHint").textContent=editor?"可导入 · 模拟操作":"只读";$("importFile").disabled=!editor;$("file").disabled=!editor;
  $("docRows").replaceChildren();state.docs.filter(d=>editor||d.scope==="售前组").forEach(d=>{const row=el("tr");row.append(el("td",d.name),el("td",d.version),el("td",d.status,d.status==="解析失败"?"failed":"pill"),el("td",d.scope));const ops=el("td");ops.append(action("预览",()=>{$("previewText").textContent=d.text;$("previewDialog").showModal();}));if(editor&&d.status==="解析失败")ops.append(action("重试",()=>{d.status="待解析";d.text="模拟重试任务已排队 尚未完成解析";renderDocs();toast("重试任务已登记");}));row.append(ops);$("docRows").append(row);});
}
$("questionForm").addEventListener("submit",e=>{e.preventDefault();submit();});
$("scenario").addEventListener("change",loadScenario);
$("reset").addEventListener("click",()=>{$("scenario").value="normal";loadScenario();toast("问答会话已重置");});
$("role").addEventListener("change",renderDocs);
document.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click",()=>showView(b.dataset.view)));
document.querySelectorAll("[data-close]").forEach(b=>b.addEventListener("click",()=>$(b.dataset.close).close()));
$("confirmTicket").addEventListener("click",()=>{const query=$("query").value.trim(),model=$("model").value,version=$("version").value,note=$("ticketNote").value.trim();const existing=state.tickets.find(t=>t.query===query&&t.model===model&&t.version===version&&t.note===note);if(existing){toast("已登记 "+existing.id);$("ticketDialog").close();return;}const id="T"+String(state.tickets.length+1).padStart(3,"0");state.tickets.push({id,query,model,version,note});$("ticketDialog").close();renderTickets();toast("已登记 "+id+" 仅当前页面保存");});
$("importFile").addEventListener("click",async()=>{
  if($("role").value!=="editor"){toast("当前角色不能导入");return;}const file=$("file").files[0];if(!file){toast("请选择文档");return;}if(file.size>20*1024*1024){toast("文件超过20MB");return;}if(state.docs.some(d=>d.name===file.name)){toast("存在同名文件 请先确认版本");return;}
  const extension=file.name.split(".").pop().toLowerCase();if(!["txt","md","pdf","docx"].includes(extension)){toast("文件类型不支持");return;}
  const doc={id:"D"+String(state.docs.length+1).padStart(2,"0"),name:file.name,version:"待补全",scope:"资料维护组",status:"待解析",text:"尚未解析"};
  if(["txt","md"].includes(extension)){try{doc.text=(await file.text()).slice(0,20000);doc.status=doc.text.trim()?"草稿":"解析失败";}catch{doc.status="解析失败";doc.text="无法读取文件";}}
  state.docs.push(doc);renderDocs();toast("文件仅在浏览器内处理 未发送到服务器");
});
loadScenario();renderDocs();renderTickets();

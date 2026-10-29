// Vercel serverless endpoint: the key is stored only in deployment environment variables.
export default async function handler(req,res){
  if(req.method!=='POST') return res.status(405).json({error:'仅支持 POST'});
  const key=process.env.VISION_API_KEY;
  if(!key) return res.status(503).json({error:'在线视觉识别尚未配置'});
  const {image}=req.body||{};
  if(typeof image!=='string'||!/^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(image)||image.length>7_000_000) return res.status(400).json({error:'请提供不超过约5MB的JPG、PNG或WebP图片'});
  const base=(process.env.VISION_BASE_URL||'https://api.openai.com/v1').replace(/\/$/,'');
  const model=process.env.VISION_MODEL||'gpt-4o-mini';
  try{
    const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),22000);
    let response;
    try{response=await fetch(`${base}/chat/completions`,{method:'POST',signal:controller.signal,headers:{'Content-Type':'application/json','Authorization':`Bearer ${key}`},body:JSON.stringify({model,max_tokens:360,temperature:0.1,messages:[{role:'system',content:'你是面向小学生的海洋生物科普助手。请根据图像识别生物，若非海洋生物、无法确定或图像不清楚，明确说无法确定，不能编造。只返回JSON对象，字段name（中文名称或无法确定）、confidence（高/中/低，主观判断）、reason（可见图像依据，50字以内）、knowledge（生态科普，80字以内）、caution（识别限制或不确定性说明，50字以内）。不要使用markdown。'},{role:'user',content:[{type:'text',text:'请识别这张图片中的海洋生物，并解释判断依据。'},{type:'image_url',image_url:{url:image}}]}]})});}finally{clearTimeout(timeout)}
    if(!response.ok) return res.status(502).json({error:'视觉服务暂时不可用，请稍后重试'});
    const raw=await response.json();const content=raw?.choices?.[0]?.message?.content;
    if(typeof content!=='string')return res.status(502).json({error:'视觉模型没有返回可读取内容'});
    const cleaned=content.replace(/^```(?:json)?\s*/,'').replace(/\s*```$/,'').trim();const result=JSON.parse(cleaned);
    return res.status(200).json({name:String(result.name||'无法确定').slice(0,80),confidence:['高','中','低'].includes(result.confidence)?result.confidence:'低',reason:String(result.reason||'').slice(0,240),knowledge:String(result.knowledge||'').slice(0,360),caution:String(result.caution||'').slice(0,240)});
  }catch{return res.status(502).json({error:'视觉模型响应失败，可能是超时或格式不兼容'});}
}

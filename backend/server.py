"""Minimal local-only visual-model gateway for ocean.dnk.cc, Python standard library."""
import base64, json, os, re, threading, time, urllib.request, urllib.parse, urllib.error, ipaddress, logging, sqlite3, secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
from collections import defaultdict, deque

HOST='127.0.0.1'; PORT=int(os.getenv('PORT','18080'))
LIMIT=7_000_000
lock=threading.Lock(); recent=defaultdict(deque)
GAME_DB=os.getenv('GAME_DB','/var/lib/weizek/guardian.sqlite3')
GAME_SECONDS=75
GAME_LIMIT=16000

def game_connection():
    conn=sqlite3.connect(GAME_DB,timeout=5)
    conn.execute('CREATE TABLE IF NOT EXISTS scores (id INTEGER PRIMARY KEY CHECK(id=1), high INTEGER NOT NULL DEFAULT 0)')
    conn.execute('INSERT OR IGNORE INTO scores(id,high) VALUES(1,0)')
    conn.execute('CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, started INTEGER NOT NULL, used INTEGER NOT NULL DEFAULT 0)')
    conn.commit()
    return conn

def game_best():
    with game_connection() as conn: return conn.execute('SELECT high FROM scores WHERE id=1').fetchone()[0]


class Handler(BaseHTTPRequestHandler):
    def respond(self,status,data):
        content=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Length',str(len(content))); self.end_headers(); self.wfile.write(content)
    def do_GET(self):
        if self.path=='/api/health': self.respond(200,{'ok':True,'vision_configured':bool(os.getenv('VISION_API_KEY'))})
        elif self.path=='/api/game-record':
            try:self.respond(200,{'best':game_best()})
            except Exception:logging.exception('game_get_error');self.respond(503,{'error':'最高纪录暂不可用'})
        else: self.respond(404,{'error':'not found'})
    def do_POST(self):
        if self.path=='/api/game-start':
            try:
                token=secrets.token_urlsafe(28)
                with game_connection() as conn:
                    conn.execute('DELETE FROM sessions WHERE started<?',(int(time.time())-86400,))
                    conn.execute('INSERT INTO sessions(token,started) VALUES(?,?)',(token,int(time.time())))
                return self.respond(200,{'token':token,'best':game_best()})
            except Exception:logging.exception('game_start_error');return self.respond(503,{'error':'纪录服务不可用'})
        if self.path=='/api/game-record':
            ip=self.headers.get('X-Real-IP',self.client_address[0]);now=time.monotonic()
            with lock:
                d=recent[('game',ip)]
                while d and now-d[0]>60:d.popleft()
                if len(d)>=12:return self.respond(429,{'error':'操作过于频繁'})
                d.append(now)
            try:
                n=int(self.headers.get('Content-Length','0'))
                if n<1 or n>1024:return self.respond(413,{'error':'请求过大'})
                data=json.loads(self.rfile.read(n));token=data.get('token');score=data.get('score')
                if not isinstance(token,str) or len(token)>128 or type(score) is not int or not 0<=score<=GAME_LIMIT:return self.respond(400,{'error':'成绩无效'})
                with game_connection() as conn:
                    conn.execute('BEGIN IMMEDIATE')
                    row=conn.execute('SELECT started,used FROM sessions WHERE token=?',(token,)).fetchone()
                    if not row or row[1] or not GAME_SECONDS-15<=int(time.time())-row[0]<=3600:return self.respond(400,{'error':'本局尚未完成或已提交'})
                    conn.execute('UPDATE sessions SET used=1 WHERE token=?',(token,))
                    best=conn.execute('SELECT high FROM scores WHERE id=1').fetchone()[0]
                    record=score>best
                    if record:conn.execute('UPDATE scores SET high=? WHERE id=1',(score,))
                    conn.commit()
                return self.respond(200,{'best':max(score,best),'new_record':record})
            except Exception:logging.exception('game_submit_error');return self.respond(503,{'error':'保存失败'})
        if self.path!='/api/identify': return self.respond(404,{'error':'not found'})
        ip=self.headers.get('X-Real-IP',self.client_address[0]);now=time.monotonic()
        with lock:
            d=recent[ip]
            while d and now-d[0]>60:d.popleft()
            if len(d)>=8:return self.respond(429,{'error':'请求过于频繁，请稍后再试'})
            d.append(now)
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n<1 or n>LIMIT:return self.respond(413,{'error':'图片过大'})
            payload=json.loads(self.rfile.read(n));image=payload.get('image','')
            if not isinstance(image,str) or len(image)>LIMIT or not re.fullmatch(r'data:image/(?:jpeg|png|webp);base64,[A-Za-z0-9+/=]+',image):return self.respond(400,{'error':'图片格式错误'})
            key=os.getenv('VISION_API_KEY','')
            if not key:return self.respond(503,{'error':'视觉模型尚未配置，其他功能可正常使用'})
            url=os.getenv('VISION_BASE_URL','https://api.openai.com/v1').rstrip('/')+'/chat/completions'
            parsed_url=urllib.parse.urlsplit(url)
            tailnet=False
            try:
                tailnet=ipaddress.ip_address(parsed_url.hostname or '').__class__.__name__=='IPv4Address' and ipaddress.ip_address(parsed_url.hostname) in ipaddress.ip_network('100.64.0.0/10')
            except ValueError: pass
            if parsed_url.scheme!='https' and not (parsed_url.scheme=='http' and tailnet):return self.respond(503,{'error':'视觉模型地址必须使用 HTTPS，或可信 Tailnet HTTP 地址'})
            model=os.getenv('VISION_MODEL','gpt-4o-mini')
            prompt='你是海洋科普助手。识别图片中的生物；不确定时必须说明无法确定，不能编造。只输出JSON对象，字段name、confidence（高/中/低）、reason、knowledge、caution，中文简洁。'
            request_body={'model':model,'temperature':0.1,'reasoning_effort':'none','max_tokens':1024,'messages':[{'role':'system','content':prompt},{'role':'user','content':[{'type':'text','text':'识别图片中的海洋生物，指出可见依据和不确定性。'},{'type':'image_url','image_url':{'url':image}}]}]}
            req=urllib.request.Request(url,json.dumps(request_body).encode(),{'Content-Type':'application/json','Authorization':'Bearer '+key},method='POST')
            with urllib.request.urlopen(req,timeout=65) as response:result=json.load(response)
            choices=result.get('choices') if isinstance(result,dict) else None
            if not isinstance(choices,list) or not choices: raise ValueError('missing_choices')
            message=choices[0].get('message') if isinstance(choices[0],dict) else None
            if not isinstance(message,dict): raise ValueError('missing_message')
            content=message.get('content')
            if isinstance(content,list):
                content='\n'.join(x.get('text','') for x in content if isinstance(x,dict) and isinstance(x.get('text'),str))
            if not isinstance(content,str) or not content.strip():
                logging.warning('vision_empty_content finish_reason=%s',str(choices[0].get('finish_reason','unknown'))[:30])
                return self.respond(502,{'error':'模型未返回可识别的内容，请更换图片或重试'})
            content=re.sub(r'^```(?:json)?\s*|\s*```$','',content.strip())
            try: parsed=json.loads(content)
            except json.JSONDecodeError:
                match=re.search(r'\{[\s\S]*\}',content)
                if match: parsed=json.loads(match.group())
                else: raise
            if not isinstance(parsed,dict):
                logging.warning('vision_wrong_json_type=%s',type(parsed).__name__)
                return self.respond(502,{'error':'模型返回的内容结构不正确，请重试'})
            output={k:str(parsed.get(k,'') or '').strip()[:maxlen] for k,maxlen in [('name',80),('confidence',8),('reason',240),('knowledge',360),('caution',240)]}
            if output['confidence'] not in ['高','中','低']:output['confidence']='低'
            self.respond(200,output)
        except urllib.error.HTTPError as e:
            logging.warning("vision_upstream_http_error code=%s", e.code)
            self.respond(502,{'error':f'视觉模型服务返回 HTTP {e.code}，请检查模型额度、输入限制或服务状态'})
        except json.JSONDecodeError:
            logging.warning("vision_model_invalid_json")
            self.respond(502,{'error':'视觉模型返回格式不符合要求，请重试'})
        except Exception as e:
            logging.warning("vision_error_type=%s detail=%s",type(e).__name__, str(e)[:80] if isinstance(e,(ValueError,AttributeError,TypeError,KeyError)) else "omitted")
            self.respond(502,{'error':'视觉识别调用失败，请稍后重试'})
    def log_message(self,format,*args):pass
if __name__=='__main__':ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()

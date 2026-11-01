"""Optional application filters. They do not alter model weights or the direct inference API."""
import re
import unicodedata
from common import CONFIG,read_json,write_json

TOPICS={
 'profanity':{'label':'Нецензурная лексика','words':['fuck','shit','бляд','блять','хуй','пизд','ебать','ёбан']},
 'adult':{'label':'Контент 18+','words':['порн','porn','эротик','explicit sex']},
 'violence':{'label':'Графическое насилие','words':['расчлен','пытк','dismember','torture']},
 'politics':{'label':'Политика','words':['политик','выборы президента','politic','presidential election']},
 'gambling':{'label':'Азартные игры','words':['казино','casino','букмекер','ставки на спорт']},
}
DEFAULT={'mode':'off','topics':[],'blocked_terms':[]}
LABELS={'off':'Без фильтров приложения','balanced':'Умеренный','strict':'Строгий','custom':'Свой'}

def config():return read_json(CONFIG/'moderation.json',{'default':DEFAULT,'models':{}})
def effective(model_id=None):
 d=config();return dict(d.get('models',{}).get(model_id,d.get('default',DEFAULT)))
def public(model_id=None):
 return {'config':config(),'effective':effective(model_id),'modes':LABELS,'topics':[{'id':k,'label':v['label']} for k,v in TOPICS.items()],
         'scope':'Фильтры веб-собеседника. Прямой llama.cpp API и Pi обходят эти проверки. Встроенные отказы модели могут сохраняться.',
         'limitations':'Проверка тем основана на словарях: она может ошибаться и не гарантирует распознавание любого перефразирования. При ограничениях ответ проверяется до показа.'}

def save(data):
 mode=data.get('mode')
 if mode not in LABELS:raise ValueError('Неизвестный режим фильтров.')
 topics=data.get('topics',[]);terms=data.get('blocked_terms',[])
 if not isinstance(topics,list) or any(t not in TOPICS for t in topics):raise ValueError('Неизвестная тема.')
 if not isinstance(terms,list) or len(terms)>100 or any(not isinstance(t,str) or not 2<=len(t.strip())<=100 for t in terms):raise ValueError('До 100 запрещённых фраз, по 2–100 символов.')
 policy={'mode':mode,'topics':list(dict.fromkeys(topics)),'blocked_terms':list(dict.fromkeys(t.strip() for t in terms))}
 model=data.get('model')
 if model is not None and (not isinstance(model,str) or not re.fullmatch('[A-Za-z0-9_.-]{1,100}',model)):raise ValueError('Неверная модель.')
 d=config()
 if model:d.setdefault('models',{})[model]=policy
 else:d['default']=policy
 write_json(CONFIG/'moderation.json',d);return public(model)

def normalize(text):return unicodedata.normalize('NFKC',text).casefold()
def check(text,policy):
 if policy.get('mode','off')=='off':return None
 folded=normalize(text)
 for term in policy.get('blocked_terms',[]):
  if normalize(term) in folded:return 'Запрещённая фраза: '+term
 for topic in policy.get('topics',[]):
  if any(normalize(word) in folded for word in TOPICS[topic]['words']):return 'Ограниченная тема: '+TOPICS[topic]['label']
 return None

def buffered(policy):return policy.get('mode')=='strict' or (policy.get('mode')!='off' and bool(policy.get('topics') or policy.get('blocked_terms')))
def instruction(policy):
 if policy.get('mode','off')=='off':return ''
 labels=[TOPICS[t]['label'] for t in policy.get('topics',[])]
 text='\nНастройки пользователя для этого разговора: отвечай без грубости.'
 if labels:text+=' Не раскрывай темы: '+', '.join(labels)+'.'
 if policy.get('blocked_terms'):text+=' Не включай запрещённые пользователем фразы: '+', '.join(policy['blocked_terms'])+'.'
 return text

"""Maintainer-only metadata refresh; no model weights are downloaded."""
import concurrent.futures
from pathlib import Path
import json
from hub import inspect_repo,from_variant
from common import write_json,ROOT
SPECS=[
('unsloth/Qwen3-4B-Instruct-2507-GGUF','Qwen 3 4B Instruct 2507','Qwen',[36,8,128],['q4_k_m','q5_k_m']),
('Qwen/Qwen3-8B-GGUF','Qwen 3 8B','Qwen',[36,8,128],['q4_k_m','q5_k_m']),
('Qwen/Qwen2.5-Coder-7B-Instruct-GGUF','Qwen 2.5 Coder 7B','Qwen',[28,4,128],['q4_k_m','q5_k_m']),
('Qwen/Qwen2.5-Coder-14B-Instruct-GGUF','Qwen 2.5 Coder 14B','Qwen',[48,8,128],['q4_k_m']),
('unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF','Qwen 3 Coder 30B A3B','Qwen',None,['q4_k_m','ud-iq2_xxs']),
('Qwen/Qwen3-0.6B-GGUF','Qwen 3 0.6B','Qwen',None,['q8_0']),
('Qwen/Qwen3-1.7B-GGUF','Qwen 3 1.7B','Qwen',None,['q8_0']),
('unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF','DeepSeek R1 Distill 1.5B','DeepSeek',[28,2,128],['q4_k_m','q5_k_m']),
('unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF','DeepSeek R1 Distill 7B','DeepSeek',[28,4,128],['q4_k_m']),
('unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF','DeepSeek R1 0528 · 8B','DeepSeek',[36,8,128],['q4_k_m','q5_k_m']),
('unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF','DeepSeek R1 Distill 14B','DeepSeek',[48,8,128],['q4_k_m']),
('unsloth/DeepSeek-R1-Distill-Qwen-32B-GGUF','DeepSeek R1 Distill 32B','DeepSeek',None,['q4_k_m']),
('unsloth/GLM-4.7-Flash-GGUF','GLM 4.7 Flash','GLM',None,['q4_k_m','ud-iq1_s','ud-iq2_xxs']),
('unsloth/Kimi-K2-Instruct-GGUF','Kimi K2 Instruct','Kimi',None,['ud-iq1_s','q4_k_m']),
('unsloth/Kimi-K2-Thinking-GGUF','Kimi K2 Thinking','Kimi',None,['ud-iq1_s']),
('bartowski/microsoft_Phi-4-mini-instruct-GGUF','Phi 4 Mini Instruct','Phi',None,['q4_k_m','q5_k_m']),
('bartowski/Mistral-7B-Instruct-v0.3-GGUF','Mistral 7B Instruct v0.3','Mistral',None,['q4_k_m','q5_k_m']),
('bartowski/Mistral-Nemo-Instruct-2407-GGUF','Mistral Nemo 12B','Mistral',None,['q4_k_m']),
('unsloth/gemma-3-4b-it-GGUF','Gemma 3 4B IT · текст','Gemma',None,['q4_k_m','q5_k_m']),
('unsloth/gemma-3-12b-it-GGUF','Gemma 3 12B IT · текст','Gemma',None,['q4_k_m']),
('bartowski/Llama-3.2-1B-Instruct-GGUF','Llama 3.2 1B Instruct','Llama',None,['q4_k_m','q8_0']),
('bartowski/Llama-3.2-3B-Instruct-GGUF','Llama 3.2 3B Instruct','Llama',None,['q4_k_m','q5_k_m']),
]
def fetch(spec):
 repo,title,family,geometry,quants=spec
 try:
  info=inspect_repo(repo);result=[]
  for quant in quants:
   match=next((v for v in info['variants'] if Path(v['variant']).name.lower().endswith('-'+quant+'.gguf')),None)
   if not match:continue
   row=from_variant(info['repo'],info['revision'],match,title+' · '+quant.upper(),family)
   if geometry:row['geometry']=geometry
   row['license']=info['license'];row['tasks']='Модель семейства '+family+'. Совместимость инструментов и качество нужно проверить на ваших задачах.'
   result.append(row)
  return result,None
 except Exception as exc:return [],repo+': '+str(exc)
if __name__=='__main__':
 rows=[];warnings=[]
 with concurrent.futures.ThreadPoolExecutor(6) as pool:
  for result,error in pool.map(fetch,SPECS):rows.extend(result);warnings.extend([error] if error else [])
 if len(rows)<20:raise RuntimeError('Недостаточно подтверждённых вариантов: '+str(warnings))
 write_json(ROOT/'assets/catalog.json',{'models':rows,'metadata_only':True})
 print('Verified variants:',len(rows),'Families:',sorted({r['family'] for r in rows}))
 for warning in warnings:print('WARNING',warning)
 for r in rows:
  if r['family']=='Kimi':print(r['name'],round(r['size']/1024**3,1),'GiB',len(r['files']),'parts')

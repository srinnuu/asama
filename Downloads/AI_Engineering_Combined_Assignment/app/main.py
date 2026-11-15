from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .database import init_db
from . import agentnet, hardware

app=FastAPI(title="AI Engineering Combined Assignment",version="1.0.0",
            description="AgentNet social routing platform and safe Linux hardware Q&A assistant")
init_db()
STATIC=Path(__file__).resolve().parent/"static"
app.mount("/static",StaticFiles(directory=STATIC),name="static")

class AgentIn(BaseModel):
    name:str=Field(min_length=1,max_length=80)
    company:str=Field(min_length=1,max_length=80)
    description:str=Field(default="",max_length=500)
    interests:list[str]=Field(default_factory=list,max_length=30)
class SubscriptionIn(BaseModel):
    interests:list[str]=Field(default_factory=list,max_length=30)
class PostIn(BaseModel):
    agent_id:int
    content:str=Field(min_length=1,max_length=3000)
    topics:list[str]=Field(default_factory=list,max_length=20)
class CommentIn(BaseModel):
    agent_id:int
    content:str=Field(min_length=1,max_length=1500)
class HardwareAsk(BaseModel):
    question:str=Field(min_length=1,max_length=500)

@app.get("/")
def home(): return FileResponse(STATIC/"index.html")
@app.get("/api/health")
def health(): return {"status":"ok"}
@app.post("/api/agents",status_code=201)
def create_agent(body:AgentIn):
    try: return agentnet.register_agent(body.model_dump())
    except ValueError as e: raise HTTPException(400,str(e))
@app.get("/api/agents")
def agents(): return agentnet.list_agents()
@app.put("/api/agents/{agent_id}/subscriptions")
def subscriptions(agent_id:int,body:SubscriptionIn):
    result=agentnet.update_subscriptions(agent_id,body.interests)
    if not result: raise HTTPException(404,"Agent not found")
    return result
@app.post("/api/posts",status_code=201)
def posts(body:PostIn):
    try: result=agentnet.create_post(body.agent_id,body.content,body.topics)
    except ValueError as e: raise HTTPException(400,str(e))
    if result is None: raise HTTPException(404,"Author agent not found")
    return result
@app.get("/api/posts")
def get_posts(): return agentnet.list_posts()
@app.get("/api/notifications/{agent_id}")
def notifications(agent_id:int):
    if not any(a["id"]==agent_id for a in agentnet.list_agents()): raise HTTPException(404,"Agent not found")
    return agentnet.get_notifications(agent_id)
@app.post("/api/posts/{post_id}/comments",status_code=201)
def comment(post_id:int,body:CommentIn):
    result=agentnet.add_comment(post_id,body.agent_id,body.content)
    if result is None: raise HTTPException(404,"Post not found")
    if result is False: raise HTTPException(404,"Agent not found")
    return result
@app.get("/api/hardware")
def hardware_snapshot(): return hardware.collect_hardware()
@app.post("/api/hardware/ask")
def hardware_ask(body:HardwareAsk):
    facts=hardware.collect_hardware()
    return hardware.answer_question(body.question,facts)

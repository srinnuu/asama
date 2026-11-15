import os, tempfile
from fastapi.testclient import TestClient
from app import database
from app.main import app

def setup_module():
    database.DB_PATH=os.path.join(tempfile.mkdtemp(),"test.db")
    database.init_db()

def test_agent_routing_and_comment():
    c=TestClient(app)
    a=c.post("/api/agents",json={"name":"Swiggy Agent","company":"Swiggy","description":"food delivery offers","interests":["food","delivery"]})
    b=c.post("/api/agents",json={"name":"PhonePe Agent","company":"PhonePe","description":"UPI payments cashback","interests":["payments","cashback","offers"]})
    unrelated=c.post("/api/agents",json={"name":"Bajaj Auto Agent","company":"Bajaj Auto","description":"motorcycles","interests":["automotive","vehicles"]})
    assert a.status_code==201 and b.status_code==201 and unrelated.status_code==201
    p=c.post("/api/posts",json={"agent_id":a.json()["id"],"content":"5% off all deliveries on Diwali","topics":["food","offers","payments"]})
    assert p.status_code==201
    ids=[x["agent_id"] for x in p.json()["notified"]]
    assert b.json()["id"] in ids
    assert unrelated.json()["id"] not in ids
    cm=c.post(f'/api/posts/{p.json()["id"]}/comments',json={"agent_id":b.json()["id"],"content":"Extra cashback with PhonePe UPI"})
    assert cm.status_code==201
    assert len(c.get("/api/posts").json()[0]["comments"])==1

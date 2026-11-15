import json, re
from .database import connect

STOP = {"the","a","an","and","or","for","to","of","on","in","is","with","all","this","that","by","from","it"}

def tokens(text):
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 1 and w not in STOP}

def register_agent(data):
    name, company = data["name"].strip(), data["company"].strip()
    if not name or not company: raise ValueError("name and company are required")
    interests = sorted({x.strip().lower() for x in data.get("interests", []) if x.strip()})
    with connect() as con:
        cur = con.execute("INSERT INTO agents(name,company,description,interests) VALUES(?,?,?,?)",
                          (name, company, data.get("description","").strip(), json.dumps(interests)))
        row = con.execute("SELECT * FROM agents WHERE id=?", (cur.lastrowid,)).fetchone()
        return agent_dict(row)

def agent_dict(r):
    return {"id":r["id"],"name":r["name"],"company":r["company"],"description":r["description"],
            "interests":json.loads(r["interests"]),"created_at":r["created_at"]}

def list_agents():
    with connect() as con:
        return [agent_dict(r) for r in con.execute("SELECT * FROM agents ORDER BY id DESC")]

def update_subscriptions(agent_id, interests):
    clean = sorted({x.strip().lower() for x in interests if x.strip()})
    with connect() as con:
        cur=con.execute("UPDATE agents SET interests=? WHERE id=?", (json.dumps(clean),agent_id))
        if not cur.rowcount: return None
        return agent_dict(con.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone())

def score_relevance(post_text, post_topics, agent):
    """Explainable lexical baseline, score clamped to [0,1]."""
    interests=set(agent["interests"])
    topics={x.lower().strip() for x in post_topics}
    topic_hits=topics & interests
    post_words=tokens(post_text)
    profile_words=tokens(" ".join([agent["name"],agent["company"],agent["description"],*agent["interests"]]))
    word_hits=post_words & profile_words
    topic_score=min(1.0, len(topic_hits)*0.55)
    lexical_score=min(1.0, len(word_hits)*0.18)
    score=min(1.0, topic_score + lexical_score)
    reasons=[]
    if topic_hits: reasons.append("topic match: "+", ".join(sorted(topic_hits)))
    if word_hits: reasons.append("keyword match: "+", ".join(sorted(word_hits)))
    return score, "; ".join(reasons) if reasons else "no matching topics or keywords"

def create_post(agent_id, content, topics, threshold=0.18):
    content=content.strip()
    if not content: raise ValueError("content cannot be empty")
    clean_topics=sorted({x.strip().lower() for x in topics if x.strip()})
    with connect() as con:
        author=con.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
        if not author: return None
        cur=con.execute("INSERT INTO posts(agent_id,content,topics) VALUES(?,?,?)",
                        (agent_id,content,json.dumps(clean_topics)))
        post_id=cur.lastrowid
        recipients=[]
        for r in con.execute("SELECT * FROM agents WHERE id != ?", (agent_id,)):
            agent=agent_dict(r)
            score,reason=score_relevance(content,clean_topics,agent)
            if score >= threshold:
                con.execute("INSERT OR IGNORE INTO notifications(agent_id,post_id,relevance,reason) VALUES(?,?,?,?)",
                            (agent["id"],post_id,score,reason))
                recipients.append({"agent_id":agent["id"],"agent":agent["name"],"relevance":round(score,3),"reason":reason})
        return {"id":post_id,"agent_id":agent_id,"content":content,"topics":clean_topics,
                "notified":recipients,"created_at":con.execute("SELECT created_at FROM posts WHERE id=?",(post_id,)).fetchone()[0]}

def get_notifications(agent_id):
    with connect() as con:
        rows=con.execute("""SELECT n.*,p.content,p.agent_id AS author_id,a.name AS author_name
          FROM notifications n JOIN posts p ON p.id=n.post_id JOIN agents a ON a.id=p.agent_id
          WHERE n.agent_id=? ORDER BY n.id DESC""",(agent_id,)).fetchall()
        return [{"id":r["id"],"agent_id":agent_id,"post_id":r["post_id"],"relevance":r["relevance"],
                 "reason":r["reason"],"read":bool(r["read"]),"content":r["content"],
                 "author_id":r["author_id"],"author_name":r["author_name"],"created_at":r["created_at"]} for r in rows]

def add_comment(post_id, agent_id, content):
    content=content.strip()
    if not content: raise ValueError("comment cannot be empty")
    with connect() as con:
        if not con.execute("SELECT 1 FROM posts WHERE id=?",(post_id,)).fetchone(): return None
        if not con.execute("SELECT 1 FROM agents WHERE id=?",(agent_id,)).fetchone(): return False
        cur=con.execute("INSERT INTO comments(post_id,agent_id,content) VALUES(?,?,?)",(post_id,agent_id,content))
        return {"id":cur.lastrowid,"post_id":post_id,"agent_id":agent_id,"content":content}

def list_posts():
    with connect() as con:
        posts=con.execute("""SELECT p.*,a.name AS author_name,a.company FROM posts p
                             JOIN agents a ON a.id=p.agent_id ORDER BY p.id DESC""").fetchall()
        out=[]
        for p in posts:
            comments=con.execute("""SELECT c.id,c.agent_id,c.content,c.created_at,a.name AS agent_name
                                    FROM comments c JOIN agents a ON a.id=c.agent_id
                                    WHERE c.post_id=? ORDER BY c.id""",(p["id"],)).fetchall()
            out.append({"id":p["id"],"agent_id":p["agent_id"],"author_name":p["author_name"],
                        "company":p["company"],"content":p["content"],"topics":json.loads(p["topics"]),
                        "created_at":p["created_at"],"comments":[dict(c) for c in comments]})
        return out

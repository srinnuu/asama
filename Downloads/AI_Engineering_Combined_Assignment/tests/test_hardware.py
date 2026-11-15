from app.hardware import answer_question

def test_ram_answer_uses_facts():
    facts={"memory":{"MemTotal":16_000_000_000,"MemAvailable":8_000_000_000}}
    result=answer_question("How much RAM do I have?",facts)
    assert "16.0 GB" in result["answer"]
    assert result["confidence"]=="high"

def test_unknown_question_does_not_guess():
    result=answer_question("What is my motherboard model?",{})
    assert "I can answer questions" in result["answer"]

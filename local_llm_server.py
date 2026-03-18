# local_llm_server.py

from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

MODEL_NAME = "unsloth/Qwen2.5-0.5B-Instruct"  # small instruct model repo

app = FastAPI(title="Local Qwen2.5-0.5B-Instruct Server")

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

print("Loading model (this may take a while the first time)...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto",
)

class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 64  # keep small for speed

class GenerateResponse(BaseModel):
    text: str

@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    prompt = req.prompt
    # Safety clamp
    max_new = min(req.max_tokens, 64)

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new,
            do_sample=False,
            temperature=0.0,
            eos_token_id=tokenizer.eos_token_id,
        )

    full_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    generated = full_text[len(prompt):].strip()
    return GenerateResponse(text=generated)

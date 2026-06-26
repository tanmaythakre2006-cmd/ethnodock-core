from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

from core.pipeline import run_autonomous_extraction
from database.supabase_client import save_master_matrix

app = FastAPI(title="Ethnodock Headless Engine")

# Implement CORSMiddleware to allow origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class ResearchRequest(BaseModel):
    herb_name: str
    api_key: str
    max_urls: int = 5

@app.post("/api/research")
async def research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """
    Executes autonomous extraction for a given herb.
    """
    try:
        master_matrix = run_autonomous_extraction(request.herb_name, request.api_key, request.max_urls)
    except Exception as e:
        logging.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error during extraction.")

    if not master_matrix:
        raise HTTPException(status_code=404, detail="No data found or extraction failed.")

    background_tasks.add_task(save_master_matrix, request.herb_name, master_matrix, ["Autonomous_Run"])

    return master_matrix

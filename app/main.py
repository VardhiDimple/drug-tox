"""DRUG TOX PRO — FastAPI application entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.schemas import DiseaseRequest, GoEnrichmentRequest, SmilesRequest
from app.services import admet_service, disease_service, go_service, ml_service, molecule_service, viz_service
from app.services.dataset_utils import dataset_preview, load_uploaded_dataset, validate_dataset_filename
from app.services.model_store import clear_model, get_model_metadata

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(
    title="DRUG TOX PRO",
    description="Drug-likeness and toxicity prediction with RDKit and scikit-learn",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    index_path = TEMPLATES_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=500, detail="Frontend template not found.")
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "app": "DRUG TOX PRO", "version": "2.0.0"}


# ——— ADMET (unchanged API) ———
@app.post("/api/admet/predict")
async def predict_admet(body: SmilesRequest) -> JSONResponse:
    try:
        result = admet_service.predict_admet(body.smiles)
        return JSONResponse({"success": True, "data": result})
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Prediction failed: {e}"}, status_code=500)


# ——— Molecular Viewer (unchanged API) ———
@app.get("/api/molecule/2d")
async def molecule_2d(smiles: str, width: int = 400, height: int = 400) -> Response:
    try:
        png = molecule_service.smiles_to_2d_png(smiles, size=(width, height))
        return Response(content=png, media_type="image/png")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/molecule/2d/base64")
async def molecule_2d_base64(smiles: str) -> JSONResponse:
    try:
        b64 = molecule_service.smiles_to_2d_base64(smiles)
        return JSONResponse({"success": True, "image_base64": b64})
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.get("/api/molecule/3d")
async def molecule_3d(smiles: str, optimize: bool = True) -> JSONResponse:
    try:
        data = molecule_service.generate_3d_structure(smiles, optimize=optimize)
        return JSONResponse({"success": True, "data": data})
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.get("/api/molecule/3d/image")
async def molecule_3d_image(smiles: str) -> Response:
    try:
        png = molecule_service.smiles_to_3d_png(smiles)
        return Response(content=png, media_type="image/png")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ——— ML Classifier ———
@app.post("/api/ml/preview")
async def ml_preview(file: UploadFile = File(...)) -> JSONResponse:
    try:
        validate_dataset_filename(file.filename)
        content = await file.read()
        df = load_uploaded_dataset(content, file.filename)
        info = dataset_preview(df)
        info["filename"] = file.filename
        return JSONResponse({"success": True, "data": info})
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.post("/api/ml/preview-columns")
async def preview_csv_columns(file: UploadFile = File(...)) -> JSONResponse:
    """Backward-compatible preview endpoint."""
    try:
        validate_dataset_filename(file.filename)
        content = await file.read()
        df = load_uploaded_dataset(content, file.filename)
        info = dataset_preview(df)
        return JSONResponse({"success": True, **info, "row_count_estimate": info["shape"]["rows"]})
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.post("/api/ml/train")
async def train_model(
    file: UploadFile = File(...),
    feature_columns: str = Form(...),
    target_column: str = Form(...),
    test_size: float = Form(0.2),
    smiles_column: str = Form(None),
) -> JSONResponse:
    try:
        validate_dataset_filename(file.filename)
        content = await file.read()
        df = load_uploaded_dataset(content, file.filename)
        features = [c.strip() for c in feature_columns.split(",") if c.strip()]
        # Backward compat: old clients send smiles_column only
        if not features and smiles_column:
            features = [smiles_column]
        result = ml_service.train_from_csv(
            df,
            feature_columns=features,
            target_column=target_column,
            test_size=test_size,
        )
        return JSONResponse({"success": True, "data": result})
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/ml/download")
async def download_model() -> Response:
    model_bytes = ml_service.get_model_bytes()
    if not model_bytes:
        raise HTTPException(status_code=404, detail="No trained model available.")
    return Response(
        content=model_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="drug_tox_pro_model.joblib"'},
    )


@app.get("/api/ml/status")
async def ml_status() -> JSONResponse:
    meta = get_model_metadata()
    return JSONResponse({"success": True, "trained": bool(meta), "metadata": meta})


@app.delete("/api/ml/model")
async def delete_model() -> JSONResponse:
    clear_model()
    return JSONResponse({"success": True, "message": "Model cleared."})


# ——— Visualization ———
@app.post("/api/viz/preview")
async def viz_preview(file: UploadFile = File(...)) -> JSONResponse:
    try:
        validate_dataset_filename(file.filename)
        content = await file.read()
        df = load_uploaded_dataset(content, file.filename)
        info = dataset_preview(df)
        return JSONResponse({"success": True, "data": info})
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.post("/api/viz/columns")
async def viz_columns(file: UploadFile = File(...)) -> JSONResponse:
    try:
        validate_dataset_filename(file.filename)
        content = await file.read()
        df = load_uploaded_dataset(content, file.filename)
        info = dataset_preview(df)
        return JSONResponse({"success": True, **info})
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.post("/api/viz/plot")
async def create_plot(
    file: UploadFile = File(...),
    plot_type: str = Form(...),
    x_column: str = Form(None),
    y_column: str = Form(None),
    color_column: str = Form(None),
    columns: str = Form(None),
) -> JSONResponse:
    try:
        validate_dataset_filename(file.filename)
        content = await file.read()
        df = load_uploaded_dataset(content, file.filename)
        col_list = [c.strip() for c in columns.split(",") if c.strip()] if columns else None
        result = viz_service.generate_plot(
            df,
            plot_type=plot_type,
            x_column=x_column or None,
            y_column=y_column or None,
            color_column=color_column or None,
            columns=col_list,
        )
        return JSONResponse({"success": True, "data": result})
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ——— GO Enrichment ———
@app.post("/api/go/enrich")
async def go_enrich(
    genes_text: str = Form(None),
    file: UploadFile = File(None),
) -> JSONResponse:
    try:
        file_content = None
        if file and file.filename:
            file_content = (await file.read()).decode("utf-8", errors="ignore")
        gene_list = go_service.parse_gene_input(text=genes_text, file_content=file_content)
        result = go_service.run_go_enrichment(gene_list)
        return JSONResponse({"success": True, "data": result})
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": f"GO enrichment failed: {e}"}, status_code=500)


@app.post("/api/go/export")
async def go_export(body: GoEnrichmentRequest) -> Response:
    try:
        genes = go_service.parse_gene_input(text=body.genes)
        result = go_service.run_go_enrichment(genes)
        return Response(
            content=result["export_csv"],
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="go_enrichment_results.csv"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ——— Disease Prediction ———
@app.post("/api/disease/predict")
async def disease_predict(body: DiseaseRequest) -> JSONResponse:
    try:
        result = disease_service.predict_disease(body.query)
        return JSONResponse({"success": True, "data": result})
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

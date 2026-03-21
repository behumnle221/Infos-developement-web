# ================================================
# main.py  →  Blog API SQLite (VERSION PROPRE)
# ================================================

from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, cast
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# ================== CONFIG ==================
app = FastAPI()

SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ================== MODÈLE BD ==================
class ArticleDB(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    titre = Column(String, nullable=False)
    contenu = Column(Text, nullable=False)
    auteur = Column(String, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    categorie = Column(String, nullable=False)
    tags = Column(JSON)

Base.metadata.create_all(bind=engine)

# ================== DB ==================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ================== SCHEMAS ==================
class ArticleBase(BaseModel):
    titre: str
    contenu: str
    auteur: str
    categorie: str
    tags: List[str] = []

class ArticleResponse(ArticleBase):
    id: int
    date: datetime

    # ✅ Pydantic v2 FIX
    model_config = ConfigDict(from_attributes=True)

# ================== ENDPOINTS ==================

@app.post("/api/articles", response_model=ArticleResponse, status_code=201)
def creer_article(article: ArticleBase, db: Session = Depends(get_db)):
    db_article = ArticleDB(**article.model_dump(), date=datetime.utcnow())
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article


@app.get("/api/articles", response_model=List[ArticleResponse])
def lire_articles(
    categorie: Optional[str] = None,
    auteur: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ArticleDB)

    if categorie:
        query = query.filter(ArticleDB.categorie == categorie)
    if auteur:
        query = query.filter(ArticleDB.auteur == auteur)

    return query.all()


@app.get("/api/articles/{id}", response_model=ArticleResponse)
def lire_un_article(id: int, db: Session = Depends(get_db)):
    article = db.query(ArticleDB).filter(ArticleDB.id == id).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article non trouvé")

    return article


@app.put("/api/articles/{id}", response_model=ArticleResponse)
def modifier_article(id: int, update: ArticleBase, db: Session = Depends(get_db)):
    article = db.query(ArticleDB).filter(ArticleDB.id == id).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article non trouvé")

    for key, value in update.model_dump().items():
        setattr(article, key, value)

    db.commit()
    db.refresh(article)
    return article


@app.delete("/api/articles/{id}")
def supprimer_article(id: int, db: Session = Depends(get_db)):
    article = db.query(ArticleDB).filter(ArticleDB.id == id).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article non trouvé")

    db.delete(article)
    db.commit()
    return {"message": "Article supprimé avec succès ✅"}


@app.get("/api/articles/search", response_model=List[ArticleResponse])
def rechercher(query: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    return db.query(ArticleDB).filter(
        (ArticleDB.titre.ilike(f"%{query}%")) |
        (ArticleDB.contenu.ilike(f"%{query}%"))
    ).all()


@app.get("/api/articles/categorie", response_model=List[ArticleResponse])
def par_categorie_et_date(
    categorie: str,
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ArticleDB).filter(ArticleDB.categorie == categorie)

    if date:
        query = query.filter(cast(ArticleDB.date, String).like(f"{date}%"))

    return query.all()


# ================== RUN ==================
# uvicorn main:app --reload
# http://127.0.0.1:8000/docs

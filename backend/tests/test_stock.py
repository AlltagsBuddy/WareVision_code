"""Tests: Lagerverwaltung und Lagerbestand."""


class TestLagerbestand:
    def _create_article(self, db, name="Testartikel", stock=10, minimum=5):
        from app.models.article import Article
        from app.models.article_category import ArticleCategory
        cat = ArticleCategory(name=f"Kategorie-{name}")
        db.add(cat)
        db.flush()
        article = Article(
            name=name,
            article_number=f"ART-{name[:4].upper()}-001",
            stock_quantity=stock,
            minimum_stock=minimum,
            purchase_price=10.00,
            sales_price_b2c=15.00,
            sales_price_b2b=12.00,
            category_id=cat.id,
        )
        db.add(article)
        db.flush()
        return article

    def test_artikel_erstellen(self, admin_client):
        """Artikel mit gültigen Daten erstellen."""
        res = admin_client.post("/api/v1/articles/", json={
            "name": "Bremsbelag vorne",
            "article_number": "BB-001",
            "purchase_price": 25.00,
            "sales_price_b2c": 49.99,
            "sales_price_b2b": 39.99,
        })
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Bremsbelag vorne"
        assert data["stock_quantity"] == 0

    def test_negativer_preis_verboten(self, admin_client):
        """Negativer Preis → 422."""
        res = admin_client.post("/api/v1/articles/", json={
            "name": "Ungültig",
            "article_number": "UNG-001",
            "purchase_price": -1.00,
            "sales_price_b2c": 10.00,
            "sales_price_b2b": 8.00,
        })
        assert res.status_code == 422

    def test_leerer_artikelname_verboten(self, admin_client):
        """Leerer Artikelname → 422."""
        res = admin_client.post("/api/v1/articles/", json={
            "name": "",
            "article_number": "LEER-001",
            "purchase_price": 10.00,
            "sales_price_b2c": 15.00,
            "sales_price_b2b": 12.00,
        })
        assert res.status_code == 422

    def test_low_stock_liste(self, admin_client, db):
        """Low-Stock-Liste enthält Artikel unter Mindestbestand."""
        self._create_article(db, name="Unterbestand", stock=2, minimum=5)
        self._create_article(db, name="Ausreichend", stock=10, minimum=5)

        res = admin_client.get("/api/v1/stock/low-stock")
        assert res.status_code == 200
        names = [a["name"] for a in res.json()]
        assert "Unterbestand" in names
        assert "Ausreichend" not in names

    def test_lagerbewegung_eingang(self, admin_client, db):
        """Wareneingang erhöht den Lagerbestand."""
        article = self._create_article(db, name="Lagereintrag", stock=5, minimum=0)

        res = admin_client.post("/api/v1/stock/movements", json={
            "article_id": str(article.id),
            "movement_type": "incoming",
            "quantity": 10,
            "notes": "Wareneingang Testlieferung",
        })
        assert res.status_code in (200, 201)

        db.expire_all()
        from app.models.article import Article
        updated = db.query(Article).filter(Article.id == article.id).first()
        assert updated.stock_quantity == 15

    def test_lagerbewegung_ausgang_unter_null_verboten(self, admin_client, db):
        """Ausgang der den Bestand unter 0 bringt → 400."""
        article = self._create_article(db, name="LagerNull", stock=3, minimum=0)

        res = admin_client.post("/api/v1/stock/movements", json={
            "article_id": str(article.id),
            "movement_type": "outgoing",
            "quantity": 10,
            "notes": "Zu viel",
        })
        assert res.status_code == 400

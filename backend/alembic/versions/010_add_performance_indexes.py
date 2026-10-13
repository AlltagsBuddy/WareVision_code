"""Performance-Indexes auf häufig gefilterten Fremdschlüsseln und Statusspalten."""

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fahrzeuge: Kundenfilter und Soft-Delete-Filter
    op.create_index("ix_vehicles_customer_id", "vehicles", ["customer_id"], if_not_exists=True)
    op.create_index("ix_vehicles_is_active", "vehicles", ["is_active"], if_not_exists=True)

    # Artikel: Barcode-Lookup, Kategorien, Status
    op.create_index("ix_articles_barcode", "articles", ["barcode"], unique=False, if_not_exists=True)
    op.create_index("ix_articles_category_id", "articles", ["category_id"], if_not_exists=True)
    op.create_index("ix_articles_is_active", "articles", ["is_active"], if_not_exists=True)

    # Werkstattaufträge: Häufige Filter
    op.create_index("ix_workshop_orders_customer_id", "workshop_orders", ["customer_id"], if_not_exists=True)
    op.create_index("ix_workshop_orders_vehicle_id", "workshop_orders", ["vehicle_id"], if_not_exists=True)
    op.create_index("ix_workshop_orders_status", "workshop_orders", ["status"], if_not_exists=True)

    # Rechnungen: Kundenfilter, Status und Fälligkeitsdatum (Mahnwesen)
    op.create_index("ix_invoices_customer_id", "invoices", ["customer_id"], if_not_exists=True)
    op.create_index("ix_invoices_status", "invoices", ["status"], if_not_exists=True)
    op.create_index("ix_invoices_due_date", "invoices", ["due_date"], if_not_exists=True)
    op.create_index("ix_invoices_workshop_order_id", "invoices", ["workshop_order_id"], if_not_exists=True)

    # Rechnungspositionen: Join über invoice_id
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"], if_not_exists=True)

    # Termine: Zeitraum-Filterung und Statusfilter
    op.create_index("ix_appointments_starts_at", "appointments", ["starts_at"], if_not_exists=True)
    op.create_index("ix_appointments_ends_at", "appointments", ["ends_at"], if_not_exists=True)
    op.create_index("ix_appointments_customer_id", "appointments", ["customer_id"], if_not_exists=True)
    op.create_index("ix_appointments_status", "appointments", ["status"], if_not_exists=True)

    # Lagerbewegungen: Artikelfilter
    op.create_index("ix_stock_movements_article_id", "stock_movements", ["article_id"], if_not_exists=True)

    # Reservierungen: Artikel + Status (Low-Stock-Query)
    op.create_index("ix_stock_reservations_article_id", "stock_reservations", ["article_id"], if_not_exists=True)
    op.create_index("ix_stock_reservations_status", "stock_reservations", ["status"], if_not_exists=True)

    # Audit-Log: Entitätstyp + ID für schnelle Abfragen
    op.create_index("ix_audit_logs_entity_type_id", "audit_logs", ["entity_type", "entity_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_entity_type_id", "audit_logs")
    op.drop_index("ix_stock_reservations_status", "stock_reservations")
    op.drop_index("ix_stock_reservations_article_id", "stock_reservations")
    op.drop_index("ix_stock_movements_article_id", "stock_movements")
    op.drop_index("ix_appointments_status", "appointments")
    op.drop_index("ix_appointments_customer_id", "appointments")
    op.drop_index("ix_appointments_ends_at", "appointments")
    op.drop_index("ix_appointments_starts_at", "appointments")
    op.drop_index("ix_invoice_items_invoice_id", "invoice_items")
    op.drop_index("ix_invoices_workshop_order_id", "invoices")
    op.drop_index("ix_invoices_due_date", "invoices")
    op.drop_index("ix_invoices_status", "invoices")
    op.drop_index("ix_invoices_customer_id", "invoices")
    op.drop_index("ix_workshop_orders_status", "workshop_orders")
    op.drop_index("ix_workshop_orders_vehicle_id", "workshop_orders")
    op.drop_index("ix_workshop_orders_customer_id", "workshop_orders")
    op.drop_index("ix_articles_is_active", "articles")
    op.drop_index("ix_articles_category_id", "articles")
    op.drop_index("ix_articles_barcode", "articles")
    op.drop_index("ix_vehicles_is_active", "vehicles")
    op.drop_index("ix_vehicles_customer_id", "vehicles")

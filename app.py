import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

# Configuración de base de datos:
# Si Render inyecta DATABASE_URL (PostgreSQL), la usa. De lo contrario, usa SQLite local.
db_url = os.environ.get("DATABASE_URL", "sqlite:///n1_assist.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Modelo de datos de Reclamo / Incidencia
class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    issue_type = db.Column(db.String(50), nullable=False) # 'corte' o 'degradacion'
    cliente = db.Column(db.String(200), nullable=False)
    servicio = db.Column(db.String(100), nullable=False)
    tipo_servicio = db.Column(db.String(50))
    horario_falla = db.Column(db.String(100))
    titulo = db.Column(db.String(250))
    domicilio = db.Column(db.String(250))
    reclama = db.Column(db.String(150))
    contacto = db.Column(db.String(150))
    horario_visita = db.Column(db.String(150))
    doc_ingreso = db.Column(db.Text)
    tech_data = db.Column(db.Text) # JSON serializado con los datos técnicos
    raw_output = db.Column(db.Text) # Plantilla final formateada

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M"),
            "issue_type": self.issue_type,
            "cliente": self.cliente,
            "servicio": self.servicio,
            "tipo_servicio": self.tipo_servicio or "",
            "horario_falla": self.horario_falla or "",
            "titulo": self.titulo or "",
            "domicilio": self.domicilio or "",
            "reclama": self.reclama or "",
            "contacto": self.contacto or "",
            "horario_visita": self.horario_visita or "",
            "doc_ingreso": self.doc_ingreso or "",
            "tech_data": json.loads(self.tech_data) if self.tech_data else {},
            "raw_output": self.raw_output or ""
        }

with app.app_context():
    db.create_all()

# Rutas estáticas (Frontend)
@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")

@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})

# Rutas de la API de Tickets
@app.route("/api/tickets", methods=["GET"])
def get_tickets():
    """Obtener listado de tickets recientes con búsqueda opcional."""
    query_str = request.args.get("q", "").strip()
    query = Ticket.query.order_by(Ticket.created_at.desc())
    
    if query_str:
        filter_str = f"%{query_str}%"
        query = query.filter(
            (Ticket.cliente.ilike(filter_str)) |
            (Ticket.servicio.ilike(filter_str)) |
            (Ticket.titulo.ilike(filter_str))
        )
    
    tickets = query.limit(50).all()
    return jsonify([t.to_dict() for t in tickets])

@app.route("/api/tickets", methods=["POST"])
def create_ticket():
    """Guardar un nuevo reclamo en la base de datos."""
    data = request.get_json() or {}
    
    if not data.get("cliente") or not data.get("servicio"):
        return jsonify({"error": "Cliente y Servicio son obligatorios"}), 400

    new_ticket = Ticket(
        issue_type=data.get("issue_type", "corte"),
        cliente=data.get("cliente", ""),
        servicio=data.get("servicio", ""),
        tipo_servicio=data.get("tipo_servicio", ""),
        horario_falla=data.get("horario_falla", ""),
        titulo=data.get("titulo", ""),
        domicilio=data.get("domicilio", ""),
        reclama=data.get("reclama", ""),
        contacto=data.get("contacto", ""),
        horario_visita=data.get("horario_visita", ""),
        doc_ingreso=data.get("doc_ingreso", ""),
        tech_data=json.dumps(data.get("tech_data", {})),
        raw_output=data.get("raw_output", "")
    )

    db.session.add(new_ticket)
    db.session.commit()

    return jsonify({"success": True, "ticket": new_ticket.to_dict()}), 201

@app.route("/api/tickets/<int:ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    """Obtener el detalle de un ticket específico."""
    ticket = Ticket.query.get_or_404(ticket_id)
    return jsonify(ticket.to_dict())

@app.route("/api/tickets/<int:ticket_id>", methods=["DELETE"])
def delete_ticket(ticket_id):
    """Eliminar un ticket."""
    ticket = Ticket.query.get_or_404(ticket_id)
    db.session.delete(ticket)
    db.session.commit()
    return jsonify({"success": True, "message": "Ticket eliminado"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

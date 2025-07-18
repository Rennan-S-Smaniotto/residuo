from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "chave-secreta"  # Necessário para usar flash messages

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'registro.db')

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIOMNS'] = False

db = SQLAlchemy(app)

class Registro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo_barras = db.Column(db.String(100), nullable=False)
    material = db.Column(db.String(100), nullable=False)
    peso_etiqueta = db.Column(db.Float, nullable=False)
    peso_balanca = db.Column(db.Float, nullable=False)
    armazenamento = db.Column(db.String(100), nullable=False)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()  # Cria as tabelas no banco de dados se não existirem

# Controle para só permitir estornar 1 vez
pode_estornar = False


@app.route('/', methods=['GET', 'POST'])
def index():
    global pode_estornar

    if request.method == 'POST':
        # Captura os dados do formulário
        codigo_barras = request.form.get('codigo_barras', '').strip()
        material = request.form.get('material', '').strip()
        peso_etiqueta = request.form.get('peso_etiqueta', '').strip()
        peso_balanca = request.form.get('peso_balanca', '').strip()
        armazenamento = request.form.get('armazenamento', '').strip()

        # Validação básica
        if not codigo_barras or not material or not peso_etiqueta or not peso_balanca or not armazenamento:
            flash("❌ Todos os campos são obrigatórios!", "danger")
            return redirect(url_for('index'))

        # Valida pesos como números
        try:
            peso_etiqueta_valor = float(peso_etiqueta)
            peso_balanca_valor = float(peso_balanca)
        except ValueError:
            flash("❌ Os pesos devem ser números válidos!", "danger")
            return redirect(url_for('index'))

        # Cria um novo registro
        novo_registro = Registro(
            codigo_barras=codigo_barras,
            material=material,
            peso_etiqueta=peso_etiqueta_valor,
            peso_balanca=peso_balanca_valor,
            armazenamento=armazenamento,
            data_hora=datetime.now()
        )

        # Adiciona o novo registro ao banco de dados
        db.session.add(novo_registro)
        db.session.commit()

        # Ativa o estorno novamente
        pode_estornar = True

        flash("✅ Registro salvo com sucesso!", "success")
        return redirect(url_for('index'))

    registros = Registro.query.order_by(Registro.data_hora.desc()).limit(5).all()
    return render_template('index.html', registros=registros, pode_estornar=pode_estornar)


@app.route('/estornar', methods=['POST'])
def estornar():
    global pode_estornar

    if not pode_estornar:
        flash("⚠ Você só pode estornar após um novo registro!", "warning")
        return redirect(url_for('index'))

    ultimo_registro = Registro.query.order_by(Registro.data_hora.desc()).first()

    if ultimo_registro:
        db.session.delete(ultimo_registro)
        db.session.commit()
        flash("✅ Último registro estornado com sucesso!", "info")
        pode_estornar = False
    else:
        flash("⚠ Nenhum registro encontrado para estornar.", "warning")

    return redirect(url_for('index'))


@app.route("/admin")
def admin_page():
    # Busca todos os registros ordenados por data
    registros = Registro.query.order_by(Registro.data_hora.desc()).all()
    return render_template("admin.html", registros=registros)

@app.route("/admin/export")
def export_excel():
    # Pega todos os registros
    registros = Registro.query.order_by(Registro.data_hora.asc()).all()

    # Converte para lista de dicionários
    data = [{
        "Código de Barras": r.codigo_barras,
        "Material": r.material,
        "Peso Etiqueta": r.peso_etiqueta,
        "Peso Balança": r.peso_balanca,
        "Armazenamento": r.armazenamento,
        "Data/Hora": r.data_hora.strftime('%d/%m/%Y %H:%M:%S')
    } for r in registros]

    # Converte para DataFrame e salva temporário
    df = pd.DataFrame(data)
    excel_path = os.path.join(BASE_DIR, "registros_export.xlsx")
    df.to_excel(excel_path, index=False)

    # Retorna o arquivo para download
    return send_file(excel_path, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)

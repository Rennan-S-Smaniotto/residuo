from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "chave-secreta"  # Necessário para usar flash messages

# ✅ Configuração do PostgreSQL no Render (External Database URL)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    'postgresql://neondb_owner:npg_zA7aoX5hkRsG@ep-holy-darkness-acrf3mjk-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ✅ Inicializando banco
db = SQLAlchemy(app)

# ✅ Modelo da Tabela
class Registro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo_barras = db.Column(db.String(100), nullable=False)
    material = db.Column(db.String(100), nullable=False)
    peso_etiqueta = db.Column(db.Float, nullable=False)
    peso_balanca = db.Column(db.Float, nullable=False)
    armazenamento = db.Column(db.String(100), nullable=False)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)

# ✅ Cria tabelas no Postgres se não existirem
with app.app_context():
    db.create_all()

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
    query = Registro.query

    # Captura filtros enviados pela URL
    codigo = request.args.get("codigo")
    material = request.args.get("material")
    armazenamento = request.args.get("armazenamento")
    data = request.args.get("data")

    if codigo:
        query = query.filter(Registro.codigo_barras.contains(codigo))
    if material:
        query = query.filter(Registro.material.contains(material))
    if armazenamento:
        query = query.filter(Registro.armazenamento == armazenamento)
    if data:
        try:
            dt = datetime.strptime(data, "%Y-%m-%d")
            dt_inicio = dt.replace(hour=0, minute=0, second=0)
            dt_fim = dt.replace(hour=23, minute=59, second=59)
            query = query.filter(Registro.data_hora >= dt_inicio, Registro.data_hora <= dt_fim)
        except ValueError:
            pass

    registros = query.order_by(Registro.data_hora.desc()).all()
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
    excel_path = os.path.join(os.getcwd(), "registros_export.xlsx")
    df = pd.DataFrame(data)
    df.to_excel(excel_path, index=False)

    # Retorna o arquivo para download
    return send_file(excel_path, as_attachment=True)


if __name__ == '__main__':
    # ✅ host='0.0.0.0' permite acesso via IP interno/externo
    app.run(host='0.0.0.0', port=5000, debug=True)

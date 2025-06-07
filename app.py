from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sprint.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# MODELOS
class Sprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)

class TareaPlanificada(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sprint_id = db.Column(db.Integer, db.ForeignKey('sprint.id'), nullable=False)
    fecha_inicio = db.Column(db.String(20))
    modulo = db.Column(db.String(100))
    codigo = db.Column(db.String(100))
    nombre = db.Column(db.String(200))

class TareaEstado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sprint_id = db.Column(db.Integer, db.ForeignKey('sprint.id'), nullable=False)
    fecha_reporte = db.Column(db.String(20))
    modulo = db.Column(db.String(100))
    codigo = db.Column(db.String(100))
    nombre = db.Column(db.String(200))
    avance = db.Column(db.String(10))

class ComparacionTarea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sprint_id = db.Column(db.Integer, db.ForeignKey('sprint.id'), nullable=False)
    codigo = db.Column(db.String(100))
    estado = db.Column(db.String(50))
    motivo = db.Column(db.String(300))
    # Para el reporte, guardamos los campos de ambas listas
    fecha_inicio = db.Column(db.String(20))
    modulo_plan = db.Column(db.String(100))
    nombre_plan = db.Column(db.String(200))
    fecha_reporte = db.Column(db.String(20))
    modulo_estado = db.Column(db.String(100))
    nombre_estado = db.Column(db.String(200))
    avance = db.Column(db.String(10))

# Inicialización de la base de datos
def init_db():
    with app.app_context():
        db.create_all()

# RUTAS
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        numero = request.form['numero']
        sprint = Sprint.query.filter_by(numero=numero).first()
        if not sprint:
            sprint = Sprint(numero=numero)
            db.session.add(sprint)
            db.session.commit()
        session['sprint_id'] = sprint.id
        return redirect(url_for('planificada'))
    return render_template('index.html')

@app.route('/planificada', methods=['GET', 'POST'])
def planificada():
    if 'sprint_id' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        tareas = []
        for i in range(len(request.form.getlist('fecha_inicio'))):
            tarea = TareaPlanificada(
                sprint_id=session['sprint_id'],
                fecha_inicio=request.form.getlist('fecha_inicio')[i],
                modulo=request.form.getlist('modulo')[i],
                codigo=request.form.getlist('codigo')[i],
                nombre=request.form.getlist('nombre')[i]
            )
            tareas.append(tarea)
        db.session.bulk_save_objects(tareas)
        db.session.commit()
        return redirect(url_for('estado'))
    return render_template('planificada.html')

@app.route('/estado', methods=['GET', 'POST'])
def estado():
    if 'sprint_id' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        tareas = []
        for i in range(len(request.form.getlist('fecha_reporte'))):
            tarea = TareaEstado(
                sprint_id=session['sprint_id'],
                fecha_reporte=request.form.getlist('fecha_reporte')[i],
                modulo=request.form.getlist('modulo')[i],
                codigo=request.form.getlist('codigo')[i],
                nombre=request.form.getlist('nombre')[i],
                avance=request.form.getlist('avance')[i]
            )
            tareas.append(tarea)
        db.session.bulk_save_objects(tareas)
        db.session.commit()
        return redirect(url_for('comparar'))
    return render_template('estado.html')

@app.route('/comparar', methods=['GET', 'POST'])
def comparar():
    if 'sprint_id' not in session:
        return redirect(url_for('index'))
    sprint_id = session['sprint_id']
    planificadas = TareaPlanificada.query.filter_by(sprint_id=sprint_id).all()
    estados = TareaEstado.query.filter_by(sprint_id=sprint_id).all()
    codigos_plan = {t.codigo: t for t in planificadas}
    codigos_estado = {t.codigo: t for t in estados}
    comparaciones = []
    motivos = {}
    # Tareas en ambas listas
    for codigo in set(codigos_plan.keys()) & set(codigos_estado.keys()):
        comparaciones.append({
            'codigo': codigo,
            'estado': 'En proceso',
            'motivo': '',
            'plan': codigos_plan[codigo],
            'estado_tarea': codigos_estado[codigo]
        })
    # Tareas no reportadas
    for codigo in set(codigos_plan.keys()) - set(codigos_estado.keys()):
        comparaciones.append({
            'codigo': codigo,
            'estado': 'No reportado',
            'motivo': '',
            'plan': codigos_plan[codigo],
            'estado_tarea': None
        })
    # Tareas nuevas
    for codigo in set(codigos_estado.keys()) - set(codigos_plan.keys()):
        comparaciones.append({
            'codigo': codigo,
            'estado': 'Nueva',
            'motivo': '',
            'plan': None,
            'estado_tarea': codigos_estado[codigo]
        })
    # Si hay motivos por registrar
    if request.method == 'POST':
        for c in comparaciones:
            motivo = request.form.get(f"motivo_{c['codigo']}", '')
            c['motivo'] = motivo
            # Guardar en la base de datos
            comp = ComparacionTarea(
                sprint_id=sprint_id,
                codigo=c['codigo'],
                estado=c['estado'],
                motivo=motivo,
                fecha_inicio=c['plan'].fecha_inicio if c['plan'] else '',
                modulo_plan=c['plan'].modulo if c['plan'] else '',
                nombre_plan=c['plan'].nombre if c['plan'] else '',
                fecha_reporte=c['estado_tarea'].fecha_reporte if c['estado_tarea'] else '',
                modulo_estado=c['estado_tarea'].modulo if c['estado_tarea'] else '',
                nombre_estado=c['estado_tarea'].nombre if c['estado_tarea'] else '',
                avance=c['estado_tarea'].avance if c['estado_tarea'] else ''
            )
            db.session.add(comp)
        db.session.commit()
        return redirect(url_for('reporte'))
    return render_template('motivos.html', comparaciones=comparaciones)

@app.route('/reporte')
def reporte():
    if 'sprint_id' not in session:
        return redirect(url_for('index'))
    sprint_id = session['sprint_id']
    comparaciones = ComparacionTarea.query.filter_by(sprint_id=sprint_id).all()
    return render_template('reporte.html', comparaciones=comparaciones)

if __name__ == '__main__':
    init_db()  # Inicializa la base de datos antes de ejecutar la app
    app.run(debug=True) 
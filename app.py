from flask import Flask, render_template, request, redirect, url_for, flash, Response, session, jsonify
from flask_mysqldb import MySQL
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import cv2
import json

# Models
from models.ModelUser import ModelUser

# Entities
from models.entities.User import User

app = Flask(__name__)
app.config.from_object('config.DevelopmentConfig')

db = MySQL(app)
login_manager_app = LoginManager(app)
login_manager_app.login_view = 'login'

cap = cv2.VideoCapture(0)
qr_detector = cv2.QRCodeDetector()

detected_qr_data = None
detected_machine_id = None

def generate():
    global detected_qr_data
    while True:
        success, frame = cap.read()
        if not success:
            continue

        data, points, _ = qr_detector.detectAndDecode(frame)

        if points is not None and data:
            try:
                qr_json = json.loads(data)
                wo_number = qr_json.get("WO")

                if wo_number:
                    detected_qr_data = wo_number

                points = points.astype(int)
                xi, yi = points[0][0][0], points[0][0][1]
                cv2.polylines(frame, [points], isClosed=True, color=(0, 255, 0), thickness=5)
                cv2.putText(frame, f'WO: {wo_number}', (xi - 15, yi - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            except Exception as e:
                cv2.putText(frame, f'QR inválido', (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.route('/confirmar-registro', methods=['GET', 'POST'])
@login_required
def confirmar_registro():
    if request.method == 'POST':
        wo = session.get('current_wo')
        maquina_id = session.get('current_machine')
        user_id = 1234

        cursor = db.connection.cursor()
        cursor.execute("SELECT * FROM produccion WHERE wo_fk = %s AND status = 1", (wo,))
        existe = cursor.fetchone()

        if existe:
            flash("Esta WO ya está en ejecución.")
            return redirect(url_for('scan'))

        cursor.execute(
            "INSERT INTO produccion (wo_fk, user_fk, status, maquina_fk) VALUES (%s, %s, %s, %s)",
            (wo, user_id, 'En proceso', maquina_id)
        )
        db.connection.commit()
        cursor.close()

        session.pop('current_wo', None)
        session.pop('current_machine', None)

        flash('Producción registrada con éxito.')
        return redirect(url_for('home'))

    wo = session.get('current_wo')
    maquina = session.get('current_machine')

    if not wo or not maquina:
        flash("Faltan datos para confirmar.")
        return redirect(url_for('scan'))

    cursor = db.connection.cursor()
    cursor.execute("SELECT * FROM ordenes WHERE WO = %s", (wo,))
    orden = cursor.fetchone()

    cursor.execute("SELECT * FROM maquinas WHERE maquina_id = %s", (maquina,))
    maquina_data = cursor.fetchone()
    cursor.close()

    return render_template('confirmar_registro.html', orden=orden, maquina=maquina_data)


@app.route('/scan-qr-maquina')
@login_required
def scan_qr_maquina():
    return render_template('scan_maquina.html')


@app.route('/procesar-maquina')
@login_required
def procesar_maquina():
    maquina_id = request.args.get('mid')
    if maquina_id:
        session['current_machine'] = maquina_id
        flash(f'Máquina {maquina_id} escaneada correctamente.', 'success')
        return redirect(url_for('confirmar_registro'))
    else:
        flash('Error al procesar la máquina.', 'danger')
        return redirect(url_for('scan_qr_maquina'))


@app.route('/video-feed-maquina')
@login_required
def video_feed_maquina():
    def generate_machine():
        global detected_machine_id
        while True:
            success, frame = cap.read()
            if not success:
                continue

            data, points, _ = qr_detector.detectAndDecode(frame)

            if points is not None and data:
                try:
                    qr_json = json.loads(data)
                    maquina_id = qr_json.get("MID")

                    if maquina_id:
                        detected_machine_id = maquina_id

                        points = points.astype(int)
                        xi, yi = points[0][0][0], points[0][0][1]
                        cv2.polylines(frame, [points], isClosed=True, color=(255, 0, 0), thickness=5)
                        cv2.putText(frame, f'MID: {maquina_id}', (xi - 15, yi - 15),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

                except Exception as e:
                    print(f"Error al leer QR: {e}")
                    cv2.putText(frame, 'QR inválido', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    return Response(generate_machine(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/process-machine-loop')
@login_required
def process_machine_loop():
    global detected_machine_id
    if detected_machine_id:
        mid = detected_machine_id
        detected_machine_id = None
        return jsonify({'status': 'ok', 'mid': mid})
    return jsonify({'status': 'waiting'})


@app.route('/verificar-produccion')
@login_required
def verificar_produccion():
    wo = session.get('current_wo')
    if not wo:
        return jsonify({'status': 'no_wo'})

    cursor = db.connection.cursor()
    cursor.execute("SELECT * FROM produccion WHERE wo_fk = %s", (wo,))
    produccion = cursor.fetchone()
    cursor.close()

    if produccion:
        return jsonify({'status': 'registrado'})
    else:
        return jsonify({'status': 'ok'})


@app.route('/video-feed')
@login_required
def video_feed():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/scan')
@login_required
def scan():
    return render_template('scanFrame.html')


@app.route('/process-qr')
@login_required
def process_qr():
    global detected_qr_data
    if detected_qr_data:
        with app.app_context():
            cursor = db.connection.cursor()

            # ✅ 1. Verificar si la orden ya está en producción con status = 1
            cursor.execute("SELECT * FROM produccion WHERE wo_fk = %s AND status = 1", (detected_qr_data,))
            produccion = cursor.fetchone()

            if produccion:
                wo = detected_qr_data
                cursor.close()
                detected_qr_data = None
                return jsonify({'status': 'ya_en_produccion', 'redirect_url': url_for("detalle_produccion", wo=wo)})

            # ✅ 2. Si no está en producción, verificar que la orden exista
            cursor.execute("SELECT * FROM ordenes WHERE WO = %s", (detected_qr_data,))
            orden = cursor.fetchone()

            cursor.close()

            if not orden:
                detected_qr_data = None
                return jsonify({'status': 'no_orden'})

            # ✅ 3. Orden válida, seguir al flujo de escaneo de máquina
            session['current_wo'] = detected_qr_data
            detected_qr_data = None
            return jsonify({'status': 'success', 'wo': session['current_wo']})

    return jsonify({'status': 'no_wo'})





@app.route('/detalle-produccion/<wo>')
@login_required
def detalle_produccion(wo):
    cursor = db.connection.cursor()
    cursor.execute("""
        SELECT p.wo_fk, p.status, p.maquina_fk, m.nombre AS nombre_maquina
        FROM produccion p
        INNER JOIN ordenes o ON p.wo_fk = o.WO
        INNER JOIN maquinas m ON p.maquina_fk = m.maquina_id
        WHERE p.wo_fk = %s
    """, (wo,))
    resultado = cursor.fetchone()

    print(resultado)
    cursor.close()

    if resultado:
        return render_template('detalle_produccion.html', datos=resultado)
    else:
        flash('No se encontraron detalles de producción.')
        return redirect(url_for('scan'))


@app.route('/orden/<int:wo>')
@login_required
def detalle_orden(wo):
    cursor = db.connection.cursor()
    cursor.execute("SELECT * FROM ordenes WHERE WO = %s", (wo,))
    orden = cursor.fetchone()
    cursor.close()

    if not orden:
        flash('Orden no encontrada')
        return redirect(url_for('scan'))

    return render_template('detalle_orden.html', orden=orden)


@login_manager_app.user_loader
def load_user(user_id):
    return ModelUser().get_by_id(db, user_id)


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    logout_user()
    if request.method == 'POST':
        user = User(0, request.form['username'], request.form['password'])
        logged_user = ModelUser().login(db, user)
        if logged_user and logged_user.password:
            login_user(logged_user)
            return redirect(url_for('home'))
        else:
            flash('Usuario o contraseña incorrectos')
    return render_template('auth/login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/home')
@login_required
def home():
    return render_template('home.html', current_user=current_user)


@app.errorhandler(401)
def status_401(error):
    return redirect(url_for('login'))


@app.errorhandler(404)
def status_404(error):
    return "<h1>Página no encontrada</h1>", 404


if __name__ == '__main__':
    app.run(debug=True)

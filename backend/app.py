import os
import re
import uuid
from datetime import date, datetime
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, request, session, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import text

load_dotenv()
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql+pg8000://postgres:12345678@localhost:5432/timary_db'
).replace('postgresql+psycopg2://', 'postgresql+pg8000://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 512 * 1024 * 1024
CORS(app, supports_credentials=True)
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(160), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # student, teacher, parent, director
    position = db.Column(db.String(120))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))


class SchoolClass(db.Model):
    __tablename__ = 'school_classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'))
    teacher = db.relationship('Teacher', foreign_keys=[teacher_id])


class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(160), nullable=False)
    position = db.Column(db.String(120), nullable=False)


class TeacherClass(db.Model):
    __tablename__ = 'teacher_classes'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'), nullable=False)
    teacher = db.relationship('Teacher')
    school_class = db.relationship('SchoolClass')
    __table_args__ = (db.UniqueConstraint('teacher_id', 'class_id', name='uq_teacher_class'),)


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(160), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'), nullable=False)
    school_class = db.relationship('SchoolClass')


class ParentChild(db.Model):
    __tablename__ = 'parent_children'
    id = db.Column(db.Integer, primary_key=True)
    parent_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    student = db.relationship('Student')


class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class Schedule(db.Model):
    __tablename__ = 'schedule'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'), nullable=False)
    week_no = db.Column(db.Integer, nullable=False, default=1)
    weekday = db.Column(db.String(20), nullable=False)
    time_start = db.Column(db.String(5), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    room = db.Column(db.String(20), nullable=False)
    school_class = db.relationship('SchoolClass')
    subject = db.relationship('Subject')
    teacher = db.relationship('Teacher')


class Homework(db.Model):
    __tablename__ = 'homework'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date_issued = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)
    school_class = db.relationship('SchoolClass')
    teacher = db.relationship('Teacher')
    subject = db.relationship('Subject')


class HomeworkSubmission(db.Model):
    __tablename__ = 'homework_submissions'
    id = db.Column(db.Integer, primary_key=True)
    homework_id = db.Column(db.Integer, db.ForeignKey('homework.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    comment = db.Column(db.Text)
    teacher_comment = db.Column(db.Text)
    status = db.Column(db.String(30), nullable=False, default='Сдано')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    homework = db.relationship('Homework')
    student = db.relationship('Student')


class Grade(db.Model):
    __tablename__ = 'grades'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    grade_date = db.Column(db.Date, nullable=False, default=date.today)
    value = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(255))
    student = db.relationship('Student')
    subject = db.relationship('Subject')
    teacher = db.relationship('Teacher')


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(30), nullable=False)
    student = db.relationship('Student')
    subject = db.relationship('Subject')


class News(db.Model):
    __tablename__ = 'news'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.String(255))
    text = db.Column(db.Text, nullable=False)
    tag = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)




def validate_password_complexity(password):
    """Возвращает список ошибок сложности пароля."""
    errors = []
    if len(password) < 8:
        errors.append('минимум 8 символов')
    if not re.search(r'[A-ZА-ЯЁ]', password):
        errors.append('хотя бы одна заглавная буква')
    if not re.search(r'[a-zа-яё]', password):
        errors.append('хотя бы одна строчная буква')
    if not re.search(r'\d', password):
        errors.append('хотя бы одна цифра')
    if not re.search(r'[^A-Za-zА-Яа-яЁё0-9]', password):
        errors.append('хотя бы один специальный символ')
    return errors


def current_user():
    user_id = session.get('user_id')
    return User.query.get(user_id) if user_id else None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return jsonify({'error': 'Требуется вход в систему'}), 401
        return fn(*args, **kwargs)
    return wrapper


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify({'error': 'Требуется вход в систему'}), 401
            if user.role not in roles:
                return jsonify({'error': 'Недостаточно прав'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def log_action(action, details=''):
    user = current_user()
    db.session.add(AuditLog(user_id=user.id if user else None, action=action, details=details))
    db.session.commit()


def as_date(value, fallback=None):
    if not value:
        return fallback or date.today()
    return datetime.strptime(value, '%Y-%m-%d').date()


def user_to_dict(user):
    return {'id': user.id, 'login': user.login, 'full_name': user.full_name, 'role': user.role, 'position': user.position, 'student_id': user.student_id}


def teacher_for_user(user):
    if not user or user.role != 'teacher':
        return None
    return Teacher.query.filter_by(full_name=user.full_name).first()


def teacher_class_ids(user):
    teacher = teacher_for_user(user)
    if not teacher:
        return []
    ids = [x.class_id for x in TeacherClass.query.filter_by(teacher_id=teacher.id).all()]
    # поддержка старых данных, где класс закреплен в school_classes.teacher_id
    ids += [c.id for c in SchoolClass.query.filter_by(teacher_id=teacher.id).all()]
    return sorted(set(ids))


def visible_student_ids(user):
    if user.role == 'student':
        return [user.student_id] if user.student_id else []
    if user.role == 'parent':
        return [pc.student_id for pc in ParentChild.query.filter_by(parent_user_id=user.id).all()]
    if user.role == 'teacher':
        class_ids = teacher_class_ids(user)
        return [s.id for s in Student.query.filter(Student.class_id.in_(class_ids)).all()] if class_ids else []
    return [s.id for s in Student.query.all()]


def require_teacher_class(class_id):
    user = current_user()
    if user.role == 'director':
        return None
    if user.role == 'teacher' and int(class_id) in teacher_class_ids(user):
        return None
    return jsonify({'error': 'Нет доступа к этому классу'}), 403


@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    # Файл доступен только авторизованным пользователям. Права на список отправок проверяются в API.
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)


@app.route('/api/public/classes')
def public_classes():
    return jsonify([{'id': c.id, 'name': c.name} for c in SchoolClass.query.order_by(SchoolClass.name).all()])


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    user = User.query.filter_by(login=data.get('login', '').strip()).first()
    if not user or not check_password_hash(user.password_hash, data.get('password', '')):
        return jsonify({'error': 'Неверный логин или пароль'}), 401
    session['user_id'] = user.id
    return jsonify({'user': user_to_dict(user)})


@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    login_value = data.get('login', '').strip()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    role = data.get('role', 'student')
    if role not in ('student', 'teacher', 'parent', 'director'):
        return jsonify({'error': 'Недопустимая роль'}), 400
    if not login_value or not password or not full_name:
        return jsonify({'error': 'Заполните ФИО, логин и пароль'}), 400
    password_errors = validate_password_complexity(password)
    if password_errors:
        return jsonify({'error': 'Пароль недостаточно сложный: ' + ', '.join(password_errors) + '.'}), 400
    if User.query.filter_by(login=login_value).first():
        return jsonify({'error': 'Такой логин уже есть'}), 400

    user = User(login=login_value, password_hash=generate_password_hash(password), full_name=full_name, role=role, position=data.get('position'))
    if role == 'student':
        class_id = data.get('class_id')
        if not class_id or not SchoolClass.query.get(class_id):
            return jsonify({'error': 'Выберите класс ученика'}), 400
        student = Student(full_name=full_name, class_id=int(class_id))
        db.session.add(student); db.session.flush()
        user.student_id = student.id
    elif role == 'teacher':
        position = data.get('position') or 'Учитель'
        teacher = Teacher(full_name=full_name, position=position)
        db.session.add(teacher)
    elif role == 'parent':
        child_id = data.get('child_id')
        db.session.add(user); db.session.flush()
        if child_id and Student.query.get(child_id):
            db.session.add(ParentChild(parent_user_id=user.id, student_id=int(child_id)))
        db.session.commit()
        return jsonify({'message': 'Пользователь создан. Теперь можно войти.'})

    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Пользователь создан. Теперь можно войти.'})


@app.route('/api/auth/me')
def me():
    user = current_user()
    return jsonify({'user': user_to_dict(user) if user else None})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Вы вышли из системы'})


@app.route('/api/meta')
@login_required
def meta():
    user = current_user()
    if user.role == 'teacher':
        class_ids = teacher_class_ids(user)
        classes = SchoolClass.query.filter(SchoolClass.id.in_(class_ids)).order_by(SchoolClass.name).all() if class_ids else []
        students = Student.query.filter(Student.class_id.in_(class_ids)).order_by(Student.full_name).all() if class_ids else []
    elif user.role == 'student':
        st = Student.query.get(user.student_id)
        classes = [st.school_class] if st else []
        students = [st] if st else []
    elif user.role == 'parent':
        ids = visible_student_ids(user)
        students = Student.query.filter(Student.id.in_(ids)).order_by(Student.full_name).all() if ids else []
        classes = list({s.school_class.id: s.school_class for s in students}.values())
    else:
        classes = SchoolClass.query.order_by(SchoolClass.name).all()
        students = Student.query.order_by(Student.full_name).all()
    return jsonify({
        'classes': [{'id': c.id, 'name': c.name, 'teacher_id': c.teacher_id} for c in classes],
        'all_classes': [{'id': c.id, 'name': c.name} for c in SchoolClass.query.order_by(SchoolClass.name).all()],
        'subjects': [{'id': s.id, 'name': s.name} for s in Subject.query.order_by(Subject.name).all()],
        'students': [{'id': s.id, 'full_name': s.full_name, 'class_id': s.class_id, 'class_name': s.school_class.name} for s in students],
        'all_students': [{'id': s.id, 'full_name': s.full_name, 'class_id': s.class_id, 'class_name': s.school_class.name} for s in Student.query.order_by(Student.full_name).all()],
        'teachers': [{'id': t.id, 'full_name': t.full_name, 'position': t.position} for t in Teacher.query.order_by(Teacher.full_name).all()],
        'assignments': [{'id': a.id, 'teacher_id': a.teacher_id, 'teacher': a.teacher.full_name, 'class_id': a.class_id, 'class_name': a.school_class.name} for a in TeacherClass.query.order_by(TeacherClass.id).all()]
    })


@app.route('/api/classes', methods=['POST'])
@roles_required('director')
def create_class():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Введите название класса'}), 400
    if SchoolClass.query.filter_by(name=name).first():
        return jsonify({'error': 'Такой класс уже есть'}), 400
    c = SchoolClass(name=name, teacher_id=data.get('teacher_id') or None)
    db.session.add(c); db.session.commit(); log_action('Создание класса', name)
    return jsonify({'id': c.id, 'name': c.name}), 201


@app.route('/api/teacher-classes', methods=['POST'])
@roles_required('director')
def assign_teacher_class():
    data = request.get_json() or {}
    teacher_id = int(data.get('teacher_id'))
    class_id = int(data.get('class_id'))
    if not Teacher.query.get(teacher_id) or not SchoolClass.query.get(class_id):
        return jsonify({'error': 'Учитель или класс не найден'}), 404
    exists = TeacherClass.query.filter_by(teacher_id=teacher_id, class_id=class_id).first()
    if exists:
        return jsonify({'message': 'Доступ уже выдан'})
    a = TeacherClass(teacher_id=teacher_id, class_id=class_id)
    db.session.add(a); db.session.commit(); log_action('Выдача доступа к классу', f'{teacher_id} -> {class_id}')
    return jsonify({'message': 'Доступ выдан'}), 201


@app.route('/api/teacher-classes/<int:assignment_id>', methods=['DELETE'])
@roles_required('director')
def delete_teacher_class(assignment_id):
    a = TeacherClass.query.get_or_404(assignment_id)
    db.session.delete(a); db.session.commit(); log_action('Удаление доступа к классу', str(assignment_id))
    return jsonify({'message': 'Доступ удален'})


@app.route('/api/schedule')
@login_required
def get_schedule():
    user = current_user()
    class_id = request.args.get('class_id', type=int)
    query = Schedule.query
    if user.role == 'student':
        st = Student.query.get(user.student_id)
        query = query.filter_by(class_id=st.class_id) if st else query.filter(False)
    elif user.role == 'parent':
        ids = visible_student_ids(user)
        class_ids = [Student.query.get(i).class_id for i in ids]
        query = query.filter(Schedule.class_id.in_(class_ids)) if class_ids else query.filter(False)
    elif user.role == 'teacher':
        class_ids = teacher_class_ids(user)
        query = query.filter(Schedule.class_id.in_(class_ids)) if class_ids else query.filter(False)
    elif class_id:
        query = query.filter_by(class_id=class_id)
    items = query.order_by(Schedule.weekday, Schedule.time_start).all()
    return jsonify([schedule_to_dict(x) for x in items])


@app.route('/api/schedule', methods=['POST'])
@roles_required('director')
def create_schedule():
    data = request.get_json() or {}
    item = Schedule(class_id=data['class_id'], week_no=data.get('week_no', 1), weekday=data['weekday'], time_start=data['time_start'], subject_id=data['subject_id'], teacher_id=data['teacher_id'], room=data['room'])
    db.session.add(item); db.session.commit(); log_action('Создание расписания', f'Урок {item.id}')
    return jsonify(schedule_to_dict(item)), 201


@app.route('/api/schedule/<int:item_id>', methods=['DELETE'])
@roles_required('director')
def delete_schedule(item_id):
    item = Schedule.query.get_or_404(item_id)
    db.session.delete(item); db.session.commit(); log_action('Удаление расписания', f'Урок {item_id}')
    return jsonify({'message': 'Запись удалена'})


def schedule_to_dict(x):
    return {'id': x.id, 'class_id': x.class_id, 'class_name': x.school_class.name, 'week_no': x.week_no, 'weekday': x.weekday, 'time_start': x.time_start, 'subject': x.subject.name, 'subject_id': x.subject_id, 'teacher': x.teacher.full_name, 'teacher_id': x.teacher_id, 'room': x.room}


@app.route('/api/homework')
@login_required
def get_homework():
    user = current_user()
    query = Homework.query
    if user.role == 'student':
        st = Student.query.get(user.student_id)
        query = query.filter_by(class_id=st.class_id) if st else query.filter(False)
    elif user.role == 'parent':
        ids = visible_student_ids(user)
        class_ids = [Student.query.get(i).class_id for i in ids]
        query = query.filter(Homework.class_id.in_(class_ids)) if class_ids else query.filter(False)
    elif user.role == 'teacher':
        class_ids = teacher_class_ids(user)
        teacher = teacher_for_user(user)
        query = query.filter(Homework.class_id.in_(class_ids), Homework.teacher_id == teacher.id) if class_ids and teacher else query.filter(False)
    items = query.order_by(Homework.due_date.desc()).all()
    student_ids = visible_student_ids(user)
    submissions = HomeworkSubmission.query.filter(HomeworkSubmission.student_id.in_(student_ids)).all() if student_ids else []
    sub_map = {(s.homework_id, s.student_id): s for s in submissions}
    result = []
    for h in items:
        status = 'Назначено'
        sub_id = None
        if user.role in ('student', 'parent') and student_ids:
            sub = sub_map.get((h.id, student_ids[0]))
            status = sub.status if sub else 'Новое'
            sub_id = sub.id if sub else None
        item = homework_to_dict(h, status)
        item['submission_id'] = sub_id
        result.append(item)
    return jsonify(result)


@app.route('/api/homework', methods=['POST'])
@roles_required('teacher')
def create_homework():
    data = request.get_json() or {}
    err = require_teacher_class(data['class_id'])
    if err:
        return err
    teacher = teacher_for_user(current_user())
    if not teacher:
        return jsonify({'error': 'Профиль учителя не найден'}), 400
    h = Homework(class_id=data['class_id'], teacher_id=teacher.id, subject_id=data['subject_id'], title=data['title'], text=data['text'], due_date=as_date(data['due_date']))
    db.session.add(h); db.session.commit(); log_action('Создание ДЗ', h.title)
    return jsonify(homework_to_dict(h)), 201


@app.route('/api/homework/<int:hw_id>/submit', methods=['POST'])
@roles_required('student')
def submit_homework(hw_id):
    hw = Homework.query.get_or_404(hw_id)
    st = Student.query.get(current_user().student_id)
    if not st or hw.class_id != st.class_id:
        return jsonify({'error': 'Нет доступа к этому заданию'}), 403
    f = request.files.get('file')
    if not f or not f.filename:
        return jsonify({'error': 'Выберите файл для отправки'}), 400
    original = secure_filename(f.filename)
    stored = f'{uuid.uuid4().hex}_{original}'
    f.save(os.path.join(UPLOAD_DIR, stored))
    old = HomeworkSubmission.query.filter_by(homework_id=hw_id, student_id=st.id).first()
    if old:
        old.file_name = original; old.stored_name = stored; old.comment = request.form.get('comment'); old.status = 'Сдано'; old.created_at = datetime.utcnow()
        sub = old
    else:
        sub = HomeworkSubmission(homework_id=hw_id, student_id=st.id, file_name=original, stored_name=stored, comment=request.form.get('comment'), status='Сдано')
        db.session.add(sub)
    db.session.commit(); log_action('Сдача ДЗ', f'ДЗ {hw_id}')
    return jsonify({'message': 'Файл отправлен учителю'})


@app.route('/api/submissions/<int:sub_id>', methods=['PATCH'])
@roles_required('teacher')
def update_submission(sub_id):
    sub = HomeworkSubmission.query.get_or_404(sub_id)
    err = require_teacher_class(sub.student.class_id)
    if err:
        return err
    teacher = teacher_for_user(current_user())
    if not teacher or sub.homework.teacher_id != teacher.id:
        return jsonify({'error': 'Можно проверять только свои задания'}), 403
    data = request.get_json() or {}
    sub.status = data.get('status', sub.status)
    sub.teacher_comment = data.get('teacher_comment', sub.teacher_comment)
    db.session.commit(); log_action('Проверка ДЗ', f'{sub_id}: {sub.status}')
    return jsonify({'message': 'Статус обновлен'})


@app.route('/api/submissions')
@roles_required('teacher', 'director')
def submissions():
    user = current_user()
    q = HomeworkSubmission.query
    if user.role == 'teacher':
        class_ids = teacher_class_ids(user)
        teacher = teacher_for_user(user)
        q = q.join(Homework).join(Student, HomeworkSubmission.student_id == Student.id).filter(Student.class_id.in_(class_ids), Homework.teacher_id == teacher.id) if class_ids and teacher else q.filter(False)
    items = q.order_by(HomeworkSubmission.created_at.desc()).all()
    return jsonify([submission_to_dict(s) for s in items])


def submission_to_dict(s):
    return {'id': s.id, 'student': s.student.full_name, 'student_id': s.student_id, 'class_name': s.student.school_class.name, 'homework': s.homework.title, 'homework_id': s.homework_id, 'subject': s.homework.subject.name, 'file_name': s.file_name, 'download_url': f'/uploads/{s.stored_name}', 'status': s.status, 'comment': s.comment, 'teacher_comment': s.teacher_comment, 'created_at': s.created_at.strftime('%d.%m.%Y %H:%M')}


def homework_to_dict(h, status='Назначено'):
    return {'id': h.id, 'class_name': h.school_class.name, 'class_id': h.class_id, 'subject': h.subject.name, 'subject_id': h.subject_id, 'teacher': h.teacher.full_name, 'teacher_id': h.teacher_id, 'title': h.title, 'text': h.text, 'date_issued': h.date_issued.isoformat(), 'due_date': h.due_date.isoformat(), 'status': status}


@app.route('/api/grades')
@login_required
def get_grades():
    user = current_user(); ids = visible_student_ids(user)
    if user.role in ('teacher', 'director') and request.args.get('student_id', type=int):
        sid = request.args.get('student_id', type=int)
        if user.role == 'teacher' and sid not in ids:
            return jsonify({'error': 'Нет доступа к этому ученику'}), 403
        ids = [sid]
    q = Grade.query.filter(Grade.student_id.in_(ids)) if ids else Grade.query.filter(False)
    if user.role == 'director' and not request.args.get('student_id'):
        q = Grade.query
    return jsonify([grade_to_dict(g) for g in q.order_by(Grade.grade_date.desc()).all()])


@app.route('/api/grades', methods=['POST'])
@roles_required('teacher', 'director')
def create_grade():
    data = request.get_json() or {}
    student = Student.query.get_or_404(data['student_id'])
    if current_user().role == 'teacher':
        err = require_teacher_class(student.class_id)
        if err:
            return err
        teacher = teacher_for_user(current_user())
        teacher_id = teacher.id
    else:
        teacher_id = data['teacher_id']
    if not 2 <= int(data['value']) <= 5:
        return jsonify({'error': 'Оценка должна быть от 2 до 5'}), 400
    g = Grade(student_id=student.id, subject_id=data['subject_id'], teacher_id=teacher_id, grade_date=as_date(data.get('grade_date')), value=int(data['value']), comment=data.get('comment'))
    db.session.add(g); db.session.commit(); log_action('Выставление оценки', f'{g.student.full_name}: {g.value}')
    return jsonify(grade_to_dict(g)), 201


def grade_to_dict(g):
    return {'id': g.id, 'student': g.student.full_name, 'student_id': g.student_id, 'class_name': g.student.school_class.name, 'subject': g.subject.name, 'subject_id': g.subject_id, 'teacher': g.teacher.full_name, 'teacher_id': g.teacher_id, 'grade_date': g.grade_date.isoformat(), 'value': g.value, 'comment': g.comment}


@app.route('/api/attendance')
@login_required
def get_attendance():
    user = current_user(); ids = visible_student_ids(user)
    if user.role in ('teacher', 'director') and request.args.get('student_id', type=int):
        sid = request.args.get('student_id', type=int)
        if user.role == 'teacher' and sid not in ids:
            return jsonify({'error': 'Нет доступа к этому ученику'}), 403
        ids = [sid]
    q = Attendance.query.filter(Attendance.student_id.in_(ids)) if ids else Attendance.query.filter(False)
    if user.role == 'director' and not request.args.get('student_id'):
        q = Attendance.query
    return jsonify([attendance_to_dict(a) for a in q.order_by(Attendance.attendance_date.desc()).all()])


@app.route('/api/attendance', methods=['POST'])
@roles_required('teacher', 'director')
def create_attendance():
    data = request.get_json() or {}
    student = Student.query.get_or_404(data['student_id'])
    if current_user().role == 'teacher':
        err = require_teacher_class(student.class_id)
        if err:
            return err
    a = Attendance(student_id=student.id, subject_id=data['subject_id'], attendance_date=as_date(data.get('attendance_date')), status=data['status'])
    db.session.add(a); db.session.commit(); log_action('Отметка посещаемости', f'{a.student.full_name}: {a.status}')
    return jsonify(attendance_to_dict(a)), 201


def attendance_to_dict(a):
    return {'id': a.id, 'student': a.student.full_name, 'student_id': a.student_id, 'class_name': a.student.school_class.name, 'subject': a.subject.name, 'subject_id': a.subject_id, 'attendance_date': a.attendance_date.isoformat(), 'status': a.status}


@app.route('/api/news')
@login_required
def get_news():
    return jsonify([{'id': n.id, 'title': n.title, 'description': n.description, 'text': n.text, 'tag': n.tag, 'created_at': n.created_at.strftime('%d.%m.%Y')} for n in News.query.order_by(News.created_at.desc()).all()])


@app.route('/api/news', methods=['POST'])
@roles_required('director')
def create_news():
    data = request.get_json() or {}
    n = News(title=data['title'], description=data.get('description'), text=data['text'], tag=data.get('tag'))
    db.session.add(n); db.session.commit(); log_action('Создание новости', n.title)
    return jsonify({'message': 'Новость создана'}), 201


@app.route('/api/news/<int:news_id>', methods=['DELETE'])
@roles_required('director')
def delete_news(news_id):
    n = News.query.get_or_404(news_id)
    db.session.delete(n); db.session.commit(); log_action('Удаление новости', n.title)
    return jsonify({'message': 'Новость удалена'})


@app.route('/api/audit')
@roles_required('director')
def audit():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(80).all()
    return jsonify([{'id': l.id, 'action': l.action, 'details': l.details, 'created_at': l.created_at.strftime('%d.%m.%Y %H:%M')} for l in logs])


def ensure_schema_updates():
    # Небольшая автоматическая миграция для пользователей, которые запускают новую версию поверх старой БД.
    # SQLAlchemy create_all создает новые таблицы, но не добавляет новые поля в уже существующие таблицы.
    with db.engine.begin() as conn:
        conn.execute(text("ALTER TABLE homework_submissions ADD COLUMN IF NOT EXISTS stored_name VARCHAR(255)"))
        conn.execute(text("ALTER TABLE homework_submissions ADD COLUMN IF NOT EXISTS teacher_comment TEXT"))
        conn.execute(text("UPDATE homework_submissions SET stored_name = file_name WHERE stored_name IS NULL OR stored_name = ''"))


def seed_data():
    if User.query.first():
        # Добавляем выдачу доступа для старой БД, если таблица пустая.
        if TeacherClass.query.count() == 0:
            for c in SchoolClass.query.all():
                if c.teacher_id:
                    db.session.add(TeacherClass(teacher_id=c.teacher_id, class_id=c.id))
            db.session.commit()
        return
    math = Subject(name='Математика'); physics = Subject(name='Физика'); inform = Subject(name='Информатика'); russian = Subject(name='Русский язык')
    db.session.add_all([math, physics, inform, russian]); db.session.flush()
    t1 = Teacher(full_name='Иванов Иван Иванович', position='Учитель математики')
    t2 = Teacher(full_name='Петрова Анна Сергеевна', position='Учитель физики')
    db.session.add_all([t1, t2]); db.session.flush()
    c10 = SchoolClass(name='10-А', teacher_id=t1.id); c9 = SchoolClass(name='9-А', teacher_id=t2.id); c11 = SchoolClass(name='11-Б', teacher_id=t1.id)
    db.session.add_all([c10, c9, c11]); db.session.flush()
    db.session.add_all([TeacherClass(teacher_id=t1.id, class_id=c10.id), TeacherClass(teacher_id=t1.id, class_id=c11.id), TeacherClass(teacher_id=t2.id, class_id=c9.id)])
    s1 = Student(full_name='Сидоров Алексей Дмитриевич', class_id=c10.id)
    s2 = Student(full_name='Иванова Мария Сергеевна', class_id=c10.id)
    s3 = Student(full_name='Петров Дмитрий Олегович', class_id=c9.id)
    db.session.add_all([s1, s2, s3]); db.session.flush()
    users = [
        User(login='student', password_hash=generate_password_hash('12345678'), full_name=s1.full_name, role='student', student_id=s1.id),
        User(login='teacher', password_hash=generate_password_hash('12345678'), full_name=t1.full_name, role='teacher', position=t1.position),
        User(login='parent', password_hash=generate_password_hash('12345678'), full_name='Сидорова Ольга Николаевна', role='parent'),
        User(login='director', password_hash=generate_password_hash('12345678'), full_name='Кузнецов Павел Андреевич', role='director', position='Директор')
    ]
    db.session.add_all(users); db.session.flush()
    db.session.add(ParentChild(parent_user_id=users[2].id, student_id=s1.id))
    db.session.add_all([
        Schedule(class_id=c10.id, week_no=1, weekday='Понедельник', time_start='09:00', subject_id=math.id, teacher_id=t1.id, room='301'),
        Schedule(class_id=c10.id, week_no=1, weekday='Понедельник', time_start='10:00', subject_id=physics.id, teacher_id=t2.id, room='210'),
        Schedule(class_id=c10.id, week_no=1, weekday='Понедельник', time_start='11:00', subject_id=inform.id, teacher_id=t1.id, room='222'),
        Schedule(class_id=c9.id, week_no=1, weekday='Вторник', time_start='09:00', subject_id=math.id, teacher_id=t1.id, room='301'),
    ])
    db.session.add_all([
        Homework(class_id=c10.id, teacher_id=t1.id, subject_id=math.id, title='Решение квадратных уравнений', text='Учебник стр. 45-47, задания №12-18', due_date=date(2026, 5, 22)),
        Homework(class_id=c10.id, teacher_id=t2.id, subject_id=physics.id, title='Законы Ньютона', text='Прочитать параграф 8 и ответить на вопросы', due_date=date(2026, 5, 24)),
    ])
    db.session.add_all([
        Grade(student_id=s1.id, subject_id=math.id, teacher_id=t1.id, grade_date=date(2026, 5, 22), value=5, comment='Отличная работа'),
        Grade(student_id=s1.id, subject_id=physics.id, teacher_id=t2.id, grade_date=date(2026, 5, 21), value=4, comment='Хорошо'),
        Grade(student_id=s2.id, subject_id=math.id, teacher_id=t1.id, grade_date=date(2026, 5, 22), value=4, comment=''),
    ])
    db.session.add_all([
        Attendance(student_id=s1.id, subject_id=math.id, attendance_date=date(2026, 5, 20), status='Присутствовал'),
        Attendance(student_id=s1.id, subject_id=physics.id, attendance_date=date(2026, 5, 21), status='Присутствовал'),
        Attendance(student_id=s2.id, subject_id=math.id, attendance_date=date(2026, 5, 20), status='Отсутствовал'),
    ])
    db.session.add_all([
        News(title='Открыта запись на курсы', description='Дополнительное образование', text='Школа открывает набор на курсы по программированию и математике.', tag='Объявление'),
        News(title='Контрольная работа', description='10-А класс', text='В пятницу пройдет контрольная по математике.', tag='Учеба')
    ])
    db.session.commit()


with app.app_context():
    db.create_all()
    ensure_schema_updates()
    seed_data()

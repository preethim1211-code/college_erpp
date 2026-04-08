from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
import sqlite3, hashlib, os, csv, io, random
from datetime import date, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = 'edusync-secret-2024'
DB = os.path.join(os.path.dirname(__file__), 'college_erp.db')

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def hash_pw(pw):   return hashlib.sha256(pw.encode()).hexdigest()
def check_pw(pw,h): return hash_pw(pw) == h

def get_grade(pct):
    if pct>=90: return 'O'
    elif pct>=80: return 'A+'
    elif pct>=70: return 'A'
    elif pct>=60: return 'B+'
    elif pct>=50: return 'B'
    elif pct>=40: return 'C'
    else: return 'F'

def login_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.','error')
            return redirect(url_for('login'))
        return f(*args,**kwargs)
    return decorated

def init_db():
    conn = get_db(); c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL,
            dept TEXT, roll_no TEXT, semester INTEGER);
        CREATE TABLE IF NOT EXISTS subjects(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL, dept TEXT, semester INTEGER,
            teacher_id INTEGER REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS attendance(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES users(id),
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            date TEXT NOT NULL, status TEXT NOT NULL,
            UNIQUE(student_id,subject_id,date));
        CREATE TABLE IF NOT EXISTS marks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES users(id),
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            exam_type TEXT NOT NULL, marks_obtained REAL NOT NULL, max_marks REAL NOT NULL,
            UNIQUE(student_id,subject_id,exam_type));
        CREATE TABLE IF NOT EXISTS timetable(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            dept TEXT, semester INTEGER);
    ''')
    conn.commit()
    if c.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
        seed(conn,c)
    conn.close()

def seed(conn,c):
    users = [
        ('Admin User','admin@college.edu',hash_pw('admin123'),'admin','Computer Science',None,None),
        ('Dr. Ramesh Kumar','ramesh@college.edu',hash_pw('teacher123'),'teacher','Computer Science',None,None),
        ('Prof. Sunita Sharma','sunita@college.edu',hash_pw('teacher123'),'teacher','Mathematics',None,None),
        ('Arjun Mehta','arjun@college.edu',hash_pw('student123'),'student','Computer Science','BCA001',6),
        ('Priya Nair','priya@college.edu',hash_pw('student123'),'student','Computer Science','BCA002',6),
        ('Rohan Desai','rohan@college.edu',hash_pw('student123'),'student','Computer Science','BCA003',6),
        ('Sneha Pillai','sneha@college.edu',hash_pw('student123'),'student','Computer Science','BCA004',6),
        ('Kiran Patel','kiran@college.edu',hash_pw('student123'),'student','Computer Science','BCA005',6),
    ]
    c.executemany('INSERT INTO users(name,email,password,role,dept,roll_no,semester) VALUES(?,?,?,?,?,?,?)',users)
    conn.commit()
    t1=c.execute("SELECT id FROM users WHERE email='ramesh@college.edu'").fetchone()[0]
    t2=c.execute("SELECT id FROM users WHERE email='sunita@college.edu'").fetchone()[0]
    subjects=[
        ('Python Programming','CS601','Computer Science',6,t1),
        ('Web Technologies','CS602','Computer Science',6,t1),
        ('Database Management','CS603','Computer Science',6,t2),
        ('Software Engineering','CS604','Computer Science',6,t2),
        ('Computer Networks','CS605','Computer Science',6,t1),
    ]
    c.executemany('INSERT INTO subjects(name,code,dept,semester,teacher_id) VALUES(?,?,?,?,?)',subjects)
    conn.commit()
    sids=[r[0] for r in c.execute('SELECT id FROM subjects ORDER BY id').fetchall()]
    stds=[r[0] for r in c.execute("SELECT id FROM users WHERE role='student' ORDER BY id").fetchall()]
    tt=[
        ('Monday','09:00','10:00',sids[0]),('Monday','10:00','11:00',sids[1]),
        ('Monday','11:15','12:15',sids[2]),('Monday','14:00','15:00',sids[3]),
        ('Tuesday','09:00','10:00',sids[2]),('Tuesday','10:00','11:00',sids[4]),
        ('Tuesday','11:15','12:15',sids[0]),('Tuesday','14:00','15:00',sids[1]),
        ('Wednesday','09:00','10:00',sids[1]),('Wednesday','10:00','11:00',sids[3]),
        ('Wednesday','11:15','12:15',sids[4]),
        ('Thursday','09:00','10:00',sids[3]),('Thursday','10:00','11:00',sids[0]),
        ('Thursday','11:15','12:15',sids[2]),('Thursday','14:00','15:00',sids[4]),
        ('Friday','09:00','10:00',sids[4]),('Friday','10:00','11:00',sids[2]),
        ('Friday','11:15','12:15',sids[1]),
    ]
    for day,st,en,sid in tt:
        c.execute('INSERT INTO timetable(day,start_time,end_time,subject_id,dept,semester) VALUES(?,?,?,?,?,?)',
                  (day,st,en,sid,'Computer Science',6))
    today=date.today(); random.seed(42)
    for sub_id in sids:
        for i in range(20):
            d=(today-timedelta(days=i)).isoformat()
            for j,sid in enumerate(stds):
                status='present' if (i+j)%5!=0 else 'absent'
                try: c.execute('INSERT INTO attendance(student_id,subject_id,date,status) VALUES(?,?,?,?)',(sid,sub_id,d,status))
                except: pass
    for sub_id in sids:
        for sid in stds:
            for etype,max_m in [('internal1',30),('internal2',30),('external',100)]:
                m=round(random.uniform(max_m*0.5,max_m),1)
                try: c.execute('INSERT INTO marks(student_id,subject_id,exam_type,marks_obtained,max_marks) VALUES(?,?,?,?,?)',(sid,sub_id,etype,m,max_m))
                except: pass
    conn.commit()

# ── AUTH ──────────────────────────────────────────────────────────────────────
@app.route('/',methods=['GET','POST'])
@app.route('/login',methods=['GET','POST'])
def login():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    if request.method=='POST':
        email=request.form.get('email','').strip()
        pw=request.form.get('password','')
        conn=get_db()
        user=conn.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        conn.close()
        if user and check_pw(pw,user['password']):
            session.update({'user_id':user['id'],'user_name':user['name'],'role':user['role'],
                            'dept':user['dept'],'semester':user['semester'],'roll_no':user['roll_no']})
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.','error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    conn=get_db(); role=session['role']; uid=session['user_id']; stats={}
    if role=='admin':
        stats['total_students']=conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
        stats['total_teachers']=conn.execute("SELECT COUNT(*) FROM users WHERE role='teacher'").fetchone()[0]
        stats['total_subjects']=conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        stats['total_records']=conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
        subs=conn.execute('SELECT * FROM subjects').fetchall()
        stats['chart_labels']=[s['code'] for s in subs]
        stats['chart_present']=[conn.execute("SELECT COUNT(*) FROM attendance WHERE subject_id=? AND status='present'",(s['id'],)).fetchone()[0] for s in subs]
        stats['chart_absent']=[conn.execute("SELECT COUNT(*) FROM attendance WHERE subject_id=? AND status='absent'",(s['id'],)).fetchone()[0] for s in subs]
    elif role=='teacher':
        my_subs=conn.execute('SELECT * FROM subjects WHERE teacher_id=?',(uid,)).fetchall()
        stats['my_subjects']=len(my_subs); stats['subjects']=my_subs
        stats['total_students']=conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
    elif role=='student':
        dept=session['dept']; sem=session['semester']
        subs=conn.execute('SELECT * FROM subjects WHERE dept=? AND semester=?',(dept,sem)).fetchall()
        att=[]
        for s in subs:
            total=conn.execute('SELECT COUNT(*) FROM attendance WHERE student_id=? AND subject_id=?',(uid,s['id'])).fetchone()[0]
            present=conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id=? AND subject_id=? AND status='present'",(uid,s['id'])).fetchone()[0]
            pct=round(present/total*100,1) if total else 0
            att.append({'subject':s,'total':total,'present':present,'pct':pct})
        mkd=[]
        for s in subs:
            recs=conn.execute('SELECT * FROM marks WHERE student_id=? AND subject_id=?',(uid,s['id'])).fetchall()
            if recs:
                avg=round(sum(r['marks_obtained']/r['max_marks']*100 for r in recs)/len(recs),1)
                mkd.append({'subject':s,'avg':avg,'grade':get_grade(avg)})
        stats.update({'attendance_data':att,'marks_data':mkd,
                      'chart_labels':[d['subject']['code'] for d in att],
                      'chart_pct':[d['pct'] for d in att]})
    conn.close()
    return render_template('dashboard.html',stats=stats)

# ── ATTENDANCE ────────────────────────────────────────────────────────────────
@app.route('/attendance')
@login_required
def attendance_index():
    conn=get_db(); role=session['role']
    if role=='student':
        uid=session['user_id']
        subs=conn.execute('SELECT * FROM subjects WHERE dept=? AND semester=?',(session['dept'],session['semester'])).fetchall()
        data=[]
        for s in subs:
            recs=conn.execute('SELECT * FROM attendance WHERE student_id=? AND subject_id=? ORDER BY date DESC',(uid,s['id'])).fetchall()
            total=len(recs); present=sum(1 for r in recs if r['status']=='present')
            pct=round(present/total*100,1) if total else 0
            data.append({'subject':s,'records':recs,'total':total,'present':present,'pct':pct})
        conn.close(); return render_template('attendance/student_view.html',data=data)
    if role=='teacher':
        subs=conn.execute('SELECT s.*,u.name as teacher_name FROM subjects s LEFT JOIN users u ON s.teacher_id=u.id WHERE s.teacher_id=?',(session['user_id'],)).fetchall()
    else:
        subs=conn.execute('SELECT s.*,u.name as teacher_name FROM subjects s LEFT JOIN users u ON s.teacher_id=u.id').fetchall()
    conn.close(); return render_template('attendance/index.html',subjects=subs)

@app.route('/attendance/mark/<int:subject_id>',methods=['GET','POST'])
@login_required
def attendance_mark(subject_id):
    if session['role']=='student': flash('Access denied.','error'); return redirect(url_for('dashboard'))
    conn=get_db()
    subject=conn.execute('SELECT * FROM subjects WHERE id=?',(subject_id,)).fetchone()
    students=conn.execute("SELECT * FROM users WHERE role='student' AND dept=? AND semester=? ORDER BY roll_no",(subject['dept'],subject['semester'])).fetchall()
    if request.method=='POST':
        att_date=request.form.get('date')
        for s in students:
            status=request.form.get(f'status_{s["id"]}','absent')
            conn.execute('INSERT OR REPLACE INTO attendance(student_id,subject_id,date,status) VALUES(?,?,?,?)',(s['id'],subject_id,att_date,status))
        conn.commit(); conn.close(); flash(f'Attendance saved for {att_date}!','success')
        return redirect(url_for('attendance_index'))
    conn.close()
    return render_template('attendance/mark.html',subject=subject,students=students,today=date.today())

@app.route('/attendance/report/<int:subject_id>')
@login_required
def attendance_report(subject_id):
    conn=get_db()
    subject=conn.execute('SELECT * FROM subjects WHERE id=?',(subject_id,)).fetchone()
    students=conn.execute("SELECT * FROM users WHERE role='student' AND dept=? AND semester=? ORDER BY roll_no",(subject['dept'],subject['semester'])).fetchall()
    data=[]
    for s in students:
        recs=conn.execute('SELECT * FROM attendance WHERE student_id=? AND subject_id=? ORDER BY date',(s['id'],subject_id)).fetchall()
        total=len(recs); present=sum(1 for r in recs if r['status']=='present')
        pct=round(present/total*100,1) if total else 0
        data.append({'student':s,'total':total,'present':present,'pct':pct})
    conn.close(); return render_template('attendance/report.html',subject=subject,report_data=data)

@app.route('/attendance/export/<int:subject_id>')
@login_required
def attendance_export(subject_id):
    conn=get_db()
    subject=conn.execute('SELECT * FROM subjects WHERE id=?',(subject_id,)).fetchone()
    students=conn.execute("SELECT * FROM users WHERE role='student' AND dept=? AND semester=? ORDER BY roll_no",(subject['dept'],subject['semester'])).fetchall()
    out=io.StringIO(); w=csv.writer(out)
    w.writerow(['Roll No','Name','Total','Present','Absent','Percentage'])
    for s in students:
        total=conn.execute('SELECT COUNT(*) FROM attendance WHERE student_id=? AND subject_id=?',(s['id'],subject_id)).fetchone()[0]
        present=conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id=? AND subject_id=? AND status='present'",(s['id'],subject_id)).fetchone()[0]
        pct=round(present/total*100,1) if total else 0
        w.writerow([s['roll_no'],s['name'],total,present,total-present,f'{pct}%'])
    conn.close()
    resp=make_response(out.getvalue())
    resp.headers['Content-Disposition']=f'attachment; filename={subject["code"]}_attendance.csv'
    resp.headers['Content-Type']='text/csv'; return resp

# ── MARKS ──────────────────────────────────────────────────────────────────────
EXAM_TYPES=[('internal1','Internal 1',30),('internal2','Internal 2',30),('external','External',100)]

@app.route('/marks')
@login_required
def marks_index():
    conn=get_db()
    if session['role']=='student':
        uid=session['user_id']
        subs=conn.execute('SELECT * FROM subjects WHERE dept=? AND semester=?',(session['dept'],session['semester'])).fetchall()
        data=[]
        for s in subs:
            recs={r['exam_type']:r for r in conn.execute('SELECT * FROM marks WHERE student_id=? AND subject_id=?',(uid,s['id'])).fetchall()}
            data.append({'subject':s,'records':recs})
        conn.close(); return render_template('marks/student_view.html',data=data,exam_types=EXAM_TYPES)
    if session['role']=='teacher':
        subs=conn.execute('SELECT s.*,u.name as teacher_name FROM subjects s LEFT JOIN users u ON s.teacher_id=u.id WHERE s.teacher_id=?',(session['user_id'],)).fetchall()
    else:
        subs=conn.execute('SELECT s.*,u.name as teacher_name FROM subjects s LEFT JOIN users u ON s.teacher_id=u.id').fetchall()
    conn.close(); return render_template('marks/index.html',subjects=subs)

@app.route('/marks/enter/<int:subject_id>',methods=['GET','POST'])
@login_required
def marks_enter(subject_id):
    if session['role']=='student': flash('Access denied.','error'); return redirect(url_for('dashboard'))
    conn=get_db()
    subject=conn.execute('SELECT * FROM subjects WHERE id=?',(subject_id,)).fetchone()
    students=conn.execute("SELECT * FROM users WHERE role='student' AND dept=? AND semester=? ORDER BY roll_no",(subject['dept'],subject['semester'])).fetchall()
    if request.method=='POST':
        exam_type=request.form.get('exam_type'); max_m={e[0]:e[2] for e in EXAM_TYPES}[exam_type]
        for s in students:
            val=request.form.get(f'marks_{s["id"]}','').strip()
            if val: conn.execute('INSERT OR REPLACE INTO marks(student_id,subject_id,exam_type,marks_obtained,max_marks) VALUES(?,?,?,?,?)',(s['id'],subject_id,exam_type,float(val),max_m))
        conn.commit(); conn.close(); flash('Marks saved successfully!','success')
        return redirect(url_for('marks_index'))
    existing={s['id']:{r['exam_type']:r for r in conn.execute('SELECT * FROM marks WHERE student_id=? AND subject_id=?',(s['id'],subject_id)).fetchall()} for s in students}
    conn.close(); return render_template('marks/enter.html',subject=subject,students=students,exam_types=EXAM_TYPES,existing_marks=existing)

@app.route('/marks/report/<int:subject_id>')
@login_required
def marks_report(subject_id):
    conn=get_db()
    subject=conn.execute('SELECT * FROM subjects WHERE id=?',(subject_id,)).fetchone()
    students=conn.execute("SELECT * FROM users WHERE role='student' AND dept=? AND semester=? ORDER BY roll_no",(subject['dept'],subject['semester'])).fetchall()
    data=[]
    for s in students:
        recs={r['exam_type']:r for r in conn.execute('SELECT * FROM marks WHERE student_id=? AND subject_id=?',(s['id'],subject_id)).fetchall()}
        pcts=[r['marks_obtained']/r['max_marks']*100 for r in recs.values()]
        avg=round(sum(pcts)/len(pcts),1) if pcts else 0
        data.append({'student':s,'records':recs,'avg':avg,'grade':get_grade(avg)})
    conn.close(); return render_template('marks/report.html',subject=subject,data=data,exam_types=EXAM_TYPES)

@app.route('/marks/export/<int:subject_id>')
@login_required
def marks_export(subject_id):
    conn=get_db()
    subject=conn.execute('SELECT * FROM subjects WHERE id=?',(subject_id,)).fetchone()
    students=conn.execute("SELECT * FROM users WHERE role='student' AND dept=? AND semester=? ORDER BY roll_no",(subject['dept'],subject['semester'])).fetchall()
    out=io.StringIO(); w=csv.writer(out)
    w.writerow(['Roll No','Name','Internal 1 (/30)','Internal 2 (/30)','External (/100)','Average %','Grade'])
    for s in students:
        recs={r['exam_type']:r for r in conn.execute('SELECT * FROM marks WHERE student_id=? AND subject_id=?',(s['id'],subject_id)).fetchall()}
        i1,i2,ex=recs.get('internal1'),recs.get('internal2'),recs.get('external')
        pcts=[r['marks_obtained']/r['max_marks']*100 for r in [i1,i2,ex] if r]
        avg=round(sum(pcts)/len(pcts),1) if pcts else 0
        w.writerow([s['roll_no'],s['name'],i1['marks_obtained'] if i1 else '-',i2['marks_obtained'] if i2 else '-',ex['marks_obtained'] if ex else '-',f'{avg}%',get_grade(avg)])
    conn.close()
    resp=make_response(out.getvalue())
    resp.headers['Content-Disposition']=f'attachment; filename={subject["code"]}_marks.csv'
    resp.headers['Content-Type']='text/csv'; return resp

# ── TIMETABLE ─────────────────────────────────────────────────────────────────
DAYS=['Monday','Tuesday','Wednesday','Thursday','Friday']
TIME_SLOTS=[('09:00','09:00–10:00'),('10:00','10:00–11:00'),('11:15','11:15–12:15'),('14:00','14:00–15:00')]

@app.route('/timetable')
@login_required
def timetable_index():
    conn=get_db()
    dept=session.get('dept') or 'Computer Science'; sem=session.get('semester') or 6
    entries=conn.execute('''SELECT t.*,s.name as sub_name,s.code as sub_code,u.name as teacher_name
        FROM timetable t JOIN subjects s ON t.subject_id=s.id LEFT JOIN users u ON s.teacher_id=u.id
        WHERE t.dept=? AND t.semester=?''',(dept,sem)).fetchall()
    conn.close()
    schedule={day:{} for day in DAYS}
    for e in entries: schedule[e['day']][e['start_time']]=e
    return render_template('timetable/index.html',schedule=schedule,days=DAYS,time_slots=TIME_SLOTS)

# ── ADMIN ──────────────────────────────────────────────────────────────────────
@app.route('/admin')
@login_required
def admin_index():
    if session['role']!='admin': flash('Admin access required.','error'); return redirect(url_for('dashboard'))
    conn=get_db()
    students=conn.execute("SELECT * FROM users WHERE role='student' ORDER BY roll_no").fetchall()
    teachers=conn.execute("SELECT * FROM users WHERE role='teacher'").fetchall()
    subjects=conn.execute('SELECT s.*,u.name as teacher_name FROM subjects s LEFT JOIN users u ON s.teacher_id=u.id').fetchall()
    conn.close(); return render_template('admin/index.html',students=students,teachers=teachers,subjects=subjects)

@app.route('/admin/add_student',methods=['POST'])
@login_required
def admin_add_student():
    if session['role']!='admin': return redirect(url_for('dashboard'))
    conn=get_db()
    try:
        conn.execute('INSERT INTO users(name,email,password,role,dept,roll_no,semester) VALUES(?,?,?,?,?,?,?)',
                     (request.form['name'],request.form['email'],hash_pw('student123'),'student',
                      request.form['dept'],request.form['roll_no'],int(request.form.get('semester',6))))
        conn.commit(); flash('Student added! Default password: student123','success')
    except sqlite3.IntegrityError: flash('Email or Roll No already exists.','error')
    conn.close(); return redirect(url_for('admin_index'))

@app.route('/admin/delete/<int:user_id>')
@login_required
def admin_delete(user_id):
    if session['role']!='admin': return redirect(url_for('dashboard'))
    conn=get_db(); conn.execute('DELETE FROM users WHERE id=?',(user_id,)); conn.commit(); conn.close()
    flash('User deleted.','success'); return redirect(url_for('admin_index'))

@app.context_processor
def inject_globals():
    return dict(current_user=session,get_grade=get_grade)

if __name__=='__main__':
    init_db(); app.run(debug=True,port=5000)

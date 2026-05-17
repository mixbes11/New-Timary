const app = document.getElementById('app');
const state = { user: null, tab: 'dashboard', meta: {classes:[], subjects:[], students:[], teachers:[], assignments:[]}, publicClasses: [] };

async function api(path, options = {}) {
  const headers = options.body instanceof FormData ? {} : {'Content-Type': 'application/json'};
  const r = await fetch('/api' + path, { credentials: 'include', headers, ...options });
  let data = {};
  try { data = await r.json(); } catch(e) {}
  if (!r.ok) throw new Error(data.error || 'Ошибка запроса');
  return data;
}
function val(id) { const el = document.getElementById(id); return el ? el.value : ''; }
function escapeHtml(s='') { return String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function opts(rows, text='name') { return rows.map(x => `<option value="${x.id}">${escapeHtml(x[text])}</option>`).join(''); }
function today() { return new Date().toISOString().slice(0,10); }
function roleRu(r) { return ({student:'Ученик', teacher:'Учитель', parent:'Родитель', director:'Директор'})[r] || r; }
function initials(name='') { return name.split(' ').filter(Boolean).slice(0,2).map(x=>x[0]).join('').toUpperCase() || 'T'; }
function message(text, type='info') { return `<div class="message ${type}">${escapeHtml(text)}</div>`; }
function passwordErrors(password='') {
  const errors = [];
  if (password.length < 8) errors.push('минимум 8 символов');
  if (!/[A-ZА-ЯЁ]/.test(password)) errors.push('заглавная буква');
  if (!/[a-zа-яё]/.test(password)) errors.push('строчная буква');
  if (!/\d/.test(password)) errors.push('цифра');
  if (!/[^A-Za-zА-Яа-яЁё0-9]/.test(password)) errors.push('спецсимвол');
  return errors;
}
function checkPasswordHint() {
  const box = document.getElementById('password_hint'); if (!box) return;
  const errors = passwordErrors(val('password'));
  box.innerHTML = errors.length ? `Пароль должен содержать: ${errors.join(', ')}.` : 'Пароль подходит.';
  box.className = errors.length ? 'hint warn' : 'hint ok';
}
function empty(text) { return `<div class="empty">${escapeHtml(text)}</div>`; }
async function loadMeta() { if (!state.user) return; state.meta = await api('/meta'); }
async function loadPublic() { try { state.publicClasses = await api('/public/classes'); } catch(e) { state.publicClasses = []; } }

async function init() {
  await loadPublic();
  const r = await api('/auth/me').catch(()=>({user:null}));
  state.user = r.user;
  if (state.user) { await loadMeta(); renderLayout(); } else renderAuth('login');
}

function renderAuth(mode='login', info='') {
  const isReg = mode === 'register';
  app.innerHTML = `
    <div class="auth-page">
      <section class="auth-hero">
        <div class="hero-logo">Timary</div>
        <h1>Электронный дневник школы</h1>
        <p>Новости, расписание, оценки, домашние задания и посещаемость в одном личном кабинете.</p>
        <div class="hero-news"><h3>Новости школы</h3><p>После входа на главной странице отображаются актуальные объявления школы.</p></div>
      </section>
      <section class="auth-card">
        <h2>${isReg ? 'Регистрация' : 'Вход'}</h2>
        ${info ? message(info, info.includes('создан') ? 'success' : 'error') : ''}
        ${isReg ? `<div class="field"><div class="label">ФИО</div><input id="full_name"></div>` : ''}
        ${isReg ? `<div class="field"><div class="label">Роль</div><select id="role" onchange="renderRegisterFields()"><option value="student">Ученик</option><option value="teacher">Учитель</option><option value="parent">Родитель</option><option value="director">Директор</option></select></div><div id="role_fields"></div>` : ''}
        <div class="field"><div class="label">Логин</div><input id="login" autocomplete="username"></div>
        <div class="field"><div class="label">Пароль</div><input id="password" type="password" autocomplete="current-password" oninput="checkPasswordHint()"></div>${isReg ? `<p id="password_hint" class="hint warn">Пароль должен содержать: минимум 8 символов, заглавную и строчную букву, цифру и спецсимвол.</p>` : ``}
        <div class="auth-actions">
          <button class="link" onclick="alert('Для восстановления доступа обратитесь к директору школы.')">Забыли пароль?</button>
          <button class="btn primary" onclick="${isReg ? 'doRegister()' : 'doLogin()'}">${isReg ? 'Зарегистрироваться' : 'Войти'}</button>
        </div>
        <div style="text-align:right;margin-top:14px"><button class="link" onclick="renderAuth('${isReg ? 'login' : 'register'}')">${isReg ? 'Есть аккаунт? Войти' : 'Регистрация'}</button></div>
      </section>
    </div>`;
  if (isReg) renderRegisterFields();
}
function renderRegisterFields() {
  const role = val('role');
  const box = document.getElementById('role_fields'); if (!box) return;
  if (role === 'student') box.innerHTML = `<div class="field"><div class="label">Класс</div><select id="class_id">${opts(state.publicClasses)}</select></div>`;
  else if (role === 'teacher') box.innerHTML = `<div class="field"><div class="label">Должность</div><input id="position" placeholder="Учитель математики"></div><p class="hint">Доступ к классам после регистрации выдает директор.</p>`;
  else if (role === 'parent') box.innerHTML = `<p class="hint">После регистрации директор или администратор может связать родителя с учеником в базе. Просмотр данных появится после привязки.</p>`;
  else box.innerHTML = `<div class="field"><div class="label">Должность</div><input id="position" value="Директор"></div>`;
}
async function doLogin() {
  try { const r = await api('/auth/login', {method:'POST', body: JSON.stringify({login:val('login'), password:val('password')})}); state.user = r.user; state.tab='dashboard'; await loadMeta(); renderLayout(); }
  catch(e) { renderAuth('login', e.message); }
}
async function doRegister() {
  try {
    const errors = passwordErrors(val('password'));
    if (errors.length) throw new Error('Пароль недостаточно сложный: ' + errors.join(', ') + '.');
    const body = {login:val('login'), password:val('password'), full_name:val('full_name'), role:val('role'), position:val('position')};
    if (body.role === 'student') body.class_id = +val('class_id');
    await api('/auth/register', {method:'POST', body: JSON.stringify(body)});
    await loadPublic(); renderAuth('login', 'Пользователь создан. Теперь войдите.');
  } catch(e) { renderAuth('register', e.message); }
}
async function logout() { await api('/auth/logout', {method:'POST'}); state.user=null; renderAuth(); }

function menuFor(role) {
  if (role === 'teacher') return [
    {id:'dashboard', name:'Главная'}, {id:'classes', name:'Мои классы'}, {id:'schedule', name:'Расписание'},
    {id:'grades', name:'Журнал оценок'}, {id:'attendance', name:'Посещаемость'}, {id:'homework', name:'Домашние задания'},
    {id:'submissions', name:'Проверка ДЗ'}, {id:'news', name:'Новости'}
  ];
  if (role === 'director') return [
    {id:'dashboard', name:'Панель директора'}, {id:'users', name:'Классы и доступ'}, {id:'schedule', name:'Расписание'},
    {id:'grades', name:'Журнал оценок'}, {id:'attendance', name:'Посещаемость'}, {id:'submissions', name:'Сданные работы'},
    {id:'news', name:'Новости'}, {id:'audit', name:'Журнал действий'}
  ];
  if (role === 'parent') return [
    {id:'dashboard', name:'Главная'}, {id:'schedule', name:'Расписание'}, {id:'grades', name:'Оценки'},
    {id:'homework', name:'Домашние задания'}, {id:'attendance', name:'Посещаемость'}, {id:'news', name:'Новости'}
  ];
  return [
    {id:'dashboard', name:'Главная'}, {id:'schedule', name:'Расписание'}, {id:'grades', name:'Оценки'},
    {id:'homework', name:'Домашние задания'}, {id:'attendance', name:'Посещаемость'}, {id:'news', name:'Новости'}
  ];
}
function tabName() { return (menuFor(state.user.role).find(x => x.id === state.tab)||{}).name || 'Главная'; }
function renderLayout() {
  const menu = menuFor(state.user.role);
  app.innerHTML = `<div class="app-shell">
    <aside class="sidebar">
      <div class="brand"><span class="brand-mark"></span><span>Timary</span></div>
      <div class="user-card"><div class="avatar">${initials(state.user.full_name)}</div><div><div class="user-name">${escapeHtml(state.user.full_name)}</div><div class="user-role">${roleRu(state.user.role)}</div></div></div>
      <nav class="menu">${menu.map(m=>`<button class="${state.tab===m.id?'active':''}" onclick="setTab('${m.id}')">${m.name}</button>`).join('')}</nav>
      <div class="sidebar-footer"><button class="btn ghost" onclick="logout()">Выйти</button></div>
    </aside>
    <main class="main"><header class="topbar"><div class="top-title">Раздел <b>${tabName()}</b></div><div class="muted">${new Date().toLocaleDateString('ru-RU')}</div></header><section class="content" id="content"></section></main>
  </div>`;
  renderContent();
}
async function setTab(tab) { state.tab = tab; await loadMeta(); renderLayout(); }
function pageHeader(title, subtitle='', action='') { return `<div class="page-head"><div><h1 class="title">${title}</h1>${subtitle?`<p class="subtitle">${subtitle}</p>`:''}</div>${action}</div>`; }

async function renderContent() {
  const c = document.getElementById('content');
  try {
    if (state.tab === 'dashboard') return renderDashboard(c);
    if (state.tab === 'classes') return renderClasses(c);
    if (state.tab === 'schedule') return renderSchedule(c);
    if (state.tab === 'grades') return renderGrades(c);
    if (state.tab === 'attendance') return renderAttendance(c);
    if (state.tab === 'homework') return renderHomework(c);
    if (state.tab === 'submissions') return renderSubmissions(c);
    if (state.tab === 'news') return renderNews(c);
    if (state.tab === 'users') return renderUsers(c);
    if (state.tab === 'audit') return renderAudit(c);
  } catch(e) { c.innerHTML = message(e.message, 'error'); }
}

async function renderDashboard(c) {
  const news = await api('/news');
  c.innerHTML = `${pageHeader(state.user.role === 'director' ? 'Панель директора' : 'Главная', 'Актуальные новости и объявления школы.')}
    <div class="grid three news-grid-large">${news.length ? news.map(n => newsCard(n, false)).join('') : empty('Новостей пока нет')}</div>`;
}
function newsCard(n, controls=true) {
  return `<article class="card news-card"><span class="news-tag">${escapeHtml(n.tag || 'Новость')}</span><h3>${escapeHtml(n.title)}</h3><p>${escapeHtml(n.description || '')}</p><p>${escapeHtml(n.text || '')}</p><p class="muted">${escapeHtml(n.created_at)}</p>${controls && state.user.role==='director' ? `<button class="btn small danger" onclick="deleteNews(${n.id})">Удалить</button>` : ''}</article>`;
}

async function renderClasses(c) {
  c.innerHTML = `${pageHeader('Мои классы', 'Учитель видит только классы, доступ к которым выдал директор.')}
    <div class="grid three">${state.meta.classes.length ? state.meta.classes.map(cl => `<div class="card"><h3>${escapeHtml(cl.name)}</h3><p>Доступ открыт директором. Ученики этого класса видны в журнале и посещаемости.</p></div>`).join('') : empty('Доступ к классам пока не выдан')}</div>`;
}

async function renderSchedule(c) {
  const rows = await api('/schedule');
  const canEdit = state.user.role === 'director';
  c.innerHTML = `${pageHeader('Расписание', 'Ученики видят только свой класс, учителя — только выданные им классы.')}
    ${canEdit ? scheduleForm() : ''}
    <div class="table-wrap"><table class="table"><thead><tr><th>День</th><th>Время</th><th>Класс</th><th>Предмет</th><th>Учитель</th><th>Кабинет</th><th></th></tr></thead><tbody>
      ${rows.map(r => `<tr><td>${escapeHtml(r.weekday)}</td><td><span class="time">${r.time_start}</span></td><td>${escapeHtml(r.class_name)}</td><td>${escapeHtml(r.subject)}</td><td>${escapeHtml(r.teacher)}</td><td><span class="room">${escapeHtml(r.room)}</span></td><td>${canEdit ? `<button class="btn small" onclick="deleteSchedule(${r.id})">Удалить</button>` : ''}</td></tr>`).join('')}
    </tbody></table></div>`;
}
function scheduleForm() { return `<div class="card form-card"><h3>Добавить занятие</h3><div class="form-row five"><select id="s_class">${opts(state.meta.all_classes || state.meta.classes)}</select><select id="s_subject">${opts(state.meta.subjects)}</select><select id="s_teacher">${opts(state.meta.teachers,'full_name')}</select><input id="s_day" value="Понедельник"><input id="s_time" value="09:00"></div><div class="form-row"><input id="s_room" placeholder="Кабинет"><button class="btn primary" onclick="addSchedule()">Сохранить</button></div></div>`; }
async function addSchedule() { await api('/schedule', {method:'POST', body: JSON.stringify({class_id:+val('s_class'), subject_id:+val('s_subject'), teacher_id:+val('s_teacher'), weekday:val('s_day'), time_start:val('s_time'), room:val('s_room'), week_no:1})}); renderContent(); }
async function deleteSchedule(id) { if(confirm('Удалить занятие?')) { await api('/schedule/'+id, {method:'DELETE'}); renderContent(); } }

async function renderHomework(c) {
  const rows = await api('/homework');
  const canCreate = state.user.role === 'teacher';
  c.innerHTML = `${pageHeader('Домашние задания', canCreate ? 'Назначение ДЗ доступно только учителю.' : 'Просмотр и сдача домашних заданий.')}
    ${canCreate ? homeworkForm() : ''}
    <div class="grid two">${rows.length ? rows.map(h => homeworkCard(h)).join('') : empty('Домашних заданий пока нет')}</div>`;
}
function homeworkForm() { return `<div class="card form-card"><h3>Назначить домашнее задание</h3><div class="form-row"><select id="h_class">${opts(state.meta.classes)}</select><select id="h_subject">${opts(state.meta.subjects)}</select><input id="h_due" type="date" value="${today()}"></div><div class="form-row"><input id="h_title" placeholder="Тема"><input id="h_text" placeholder="Текст задания"><button class="btn primary" onclick="addHomework()">Создать</button></div></div>`; }
function homeworkCard(h) {
  const submit = state.user.role === 'student' ? `<div class="submit-box"><input id="file_${h.id}" type="file"><input id="comment_${h.id}" placeholder="Комментарий к работе"><button class="btn primary" onclick="submitHomework(${h.id})">Отправить файл</button></div>` : '';
  return `<div class="card homework-card"><div class="homework-top"><div><h3>${escapeHtml(h.title)}</h3><div class="muted">${escapeHtml(h.subject)} · ${escapeHtml(h.class_name)} · до ${h.due_date}</div></div><span class="status-warn">${escapeHtml(h.status)}</span></div><p>${escapeHtml(h.text)}</p>${submit}</div>`;
}
async function addHomework() { await api('/homework', {method:'POST', body: JSON.stringify({class_id:+val('h_class'), subject_id:+val('h_subject'), title:val('h_title'), text:val('h_text'), due_date:val('h_due')})}); renderContent(); }
async function submitHomework(id) {
  const inp = document.getElementById('file_'+id);
  if (!inp.files.length) return alert('Выберите файл');
  const fd = new FormData(); fd.append('file', inp.files[0]); fd.append('comment', val('comment_'+id));
  await api('/homework/'+id+'/submit', {method:'POST', body:fd}); alert('Файл отправлен'); renderContent();
}

async function renderSubmissions(c) {
  const rows = await api('/submissions');
  c.innerHTML = `${pageHeader('Проверка домашних заданий', state.user.role === 'teacher' ? 'Учитель видит только работы по своим заданиям и своим классам.' : 'Просмотр отправленных работ.')}
    <div class="table-wrap"><table class="table"><thead><tr><th>Ученик</th><th>Класс</th><th>Задание</th><th>Файл</th><th>Статус</th><th>Комментарий</th><th></th></tr></thead><tbody>
      ${rows.map(s => `<tr><td>${escapeHtml(s.student)}</td><td>${escapeHtml(s.class_name)}</td><td>${escapeHtml(s.homework)}</td><td><a href="${s.download_url}">${escapeHtml(s.file_name)}</a></td><td>${escapeHtml(s.status)}</td><td>${escapeHtml(s.comment || '')}</td><td>${state.user.role==='teacher' ? `<select id="st_${s.id}"><option>Принято</option><option>Вернуть на доработку</option><option>Сдано</option></select><input id="tc_${s.id}" placeholder="Комментарий"><button class="btn small primary" onclick="checkSubmission(${s.id})">Сохранить</button>` : ''}</td></tr>`).join('')}
    </tbody></table></div>`;
}
async function checkSubmission(id) { await api('/submissions/'+id, {method:'PATCH', body: JSON.stringify({status:val('st_'+id), teacher_comment:val('tc_'+id)})}); renderContent(); }

async function renderGrades(c) {
  const rows = await api('/grades'); const canEdit = ['teacher','director'].includes(state.user.role);
  c.innerHTML = `${pageHeader(canEdit?'Журнал оценок':'Оценки', canEdit?'Учитель видит только учеников из своих классов.':'Ваши оценки.')}
    ${canEdit ? gradeForm() : ''}
    <div class="table-wrap"><table class="table"><thead><tr><th>Дата</th><th>Ученик</th><th>Класс</th><th>Предмет</th><th>Оценка</th><th>Комментарий</th></tr></thead><tbody>${rows.map(g=>`<tr><td>${g.grade_date}</td><td>${escapeHtml(g.student)}</td><td>${escapeHtml(g.class_name)}</td><td>${escapeHtml(g.subject)}</td><td><b>${g.value}</b></td><td>${escapeHtml(g.comment||'')}</td></tr>`).join('')}</tbody></table></div>`;
}
function gradeForm() { return `<div class="card form-card"><h3>Поставить оценку</h3><div class="form-row six"><select id="g_student">${opts(state.meta.students,'full_name')}</select><select id="g_subject">${opts(state.meta.subjects)}</select>${state.user.role==='director'?`<select id="g_teacher">${opts(state.meta.teachers,'full_name')}</select>`:''}<input id="g_date" type="date" value="${today()}"><input id="g_value" type="number" min="2" max="5" value="5"><input id="g_comment" placeholder="Комментарий"><button class="btn primary" onclick="addGrade()">Сохранить</button></div></div>`; }
async function addGrade() { const body = {student_id:+val('g_student'), subject_id:+val('g_subject'), grade_date:val('g_date'), value:+val('g_value'), comment:val('g_comment')}; if(state.user.role==='director') body.teacher_id=+val('g_teacher'); await api('/grades', {method:'POST', body:JSON.stringify(body)}); renderContent(); }

async function renderAttendance(c) {
  const rows = await api('/attendance'); const canEdit = ['teacher','director'].includes(state.user.role);
  c.innerHTML = `${pageHeader('Посещаемость', canEdit?'Отметка посещаемости по ученикам доступных классов.':'Ваши отметки посещаемости.')}
    ${canEdit ? attendanceForm() : ''}
    <div class="table-wrap"><table class="table"><thead><tr><th>Дата</th><th>Ученик</th><th>Класс</th><th>Предмет</th><th>Статус</th></tr></thead><tbody>${rows.map(a=>`<tr><td>${a.attendance_date}</td><td>${escapeHtml(a.student)}</td><td>${escapeHtml(a.class_name)}</td><td>${escapeHtml(a.subject)}</td><td>${escapeHtml(a.status)}</td></tr>`).join('')}</tbody></table></div>`;
}
function attendanceForm() { return `<div class="card form-card"><h3>Отметить посещаемость</h3><div class="form-row five"><select id="a_student">${opts(state.meta.students,'full_name')}</select><select id="a_subject">${opts(state.meta.subjects)}</select><input id="a_date" type="date" value="${today()}"><select id="a_status"><option>Присутствовал</option><option>Отсутствовал</option><option>Болел</option></select><button class="btn primary" onclick="addAttendance()">Сохранить</button></div></div>`; }
async function addAttendance() { await api('/attendance', {method:'POST', body: JSON.stringify({student_id:+val('a_student'), subject_id:+val('a_subject'), attendance_date:val('a_date'), status:val('a_status')})}); renderContent(); }

async function renderNews(c) {
  const rows = await api('/news');
  c.innerHTML = `${pageHeader('Новости', 'Новости школы отображаются на главной странице.')}
    ${state.user.role==='director' ? `<div class="card form-card"><h3>Добавить новость</h3><div class="form-row"><input id="n_title" placeholder="Заголовок"><input id="n_desc" placeholder="Краткое описание"><input id="n_tag" placeholder="Пометка"></div><textarea id="n_text" placeholder="Текст новости"></textarea><div class="form-actions"><button class="btn primary" onclick="addNews()">Опубликовать</button></div></div>` : ''}
    <div class="grid three">${rows.length ? rows.map(n=>newsCard(n,true)).join('') : empty('Новостей пока нет')}</div>`;
}
async function addNews() { await api('/news', {method:'POST', body: JSON.stringify({title:val('n_title'), description:val('n_desc'), text:val('n_text'), tag:val('n_tag')})}); renderContent(); }
async function deleteNews(id) { if(confirm('Удалить новость?')) { await api('/news/'+id, {method:'DELETE'}); renderContent(); } }

async function renderUsers(c) {
  c.innerHTML = `${pageHeader('Классы и доступ учителей', 'Директор создает классы и выдает учителям доступ к нужным классам.')}
    <div class="grid two">
      <div class="card form-card"><h3>Добавить класс</h3><div class="form-row"><input id="class_name" placeholder="Например, 8-Б"><select id="class_teacher"><option value="">Классный руководитель не выбран</option>${opts(state.meta.teachers,'full_name')}</select><button class="btn primary" onclick="addClass()">Создать</button></div></div>
      <div class="card form-card"><h3>Выдать доступ учителю</h3><div class="form-row"><select id="assign_teacher">${opts(state.meta.teachers,'full_name')}</select><select id="assign_class">${opts(state.meta.all_classes || state.meta.classes)}</select><button class="btn primary" onclick="assignClass()">Выдать</button></div></div>
    </div>
    <div class="grid two">
      <div class="card"><h3>Все классы</h3>${(state.meta.all_classes||[]).map(cl=>`<div class="line">${escapeHtml(cl.name)}</div>`).join('') || empty('Классов нет')}</div>
      <div class="card"><h3>Доступы учителей</h3>${state.meta.assignments.length ? state.meta.assignments.map(a=>`<div class="line"><span>${escapeHtml(a.teacher)} → <b>${escapeHtml(a.class_name)}</b></span><button class="btn small" onclick="removeAssignment(${a.id})">Удалить</button></div>`).join('') : empty('Доступы не выданы')}</div>
    </div>
    <div class="card"><h3>Ученики</h3><div class="table-wrap"><table class="table"><thead><tr><th>ФИО</th><th>Класс</th></tr></thead><tbody>${(state.meta.all_students||[]).map(s=>`<tr><td>${escapeHtml(s.full_name)}</td><td>${escapeHtml(s.class_name)}</td></tr>`).join('')}</tbody></table></div></div>`;
}
async function addClass() { await api('/classes', {method:'POST', body:JSON.stringify({name:val('class_name'), teacher_id: val('class_teacher') || null})}); await loadMeta(); renderContent(); }
async function assignClass() { await api('/teacher-classes', {method:'POST', body:JSON.stringify({teacher_id:+val('assign_teacher'), class_id:+val('assign_class')})}); await loadMeta(); renderContent(); }
async function removeAssignment(id) { await api('/teacher-classes/'+id, {method:'DELETE'}); await loadMeta(); renderContent(); }

async function renderAudit(c) {
  const rows = await api('/audit');
  c.innerHTML = `${pageHeader('Журнал действий', 'Последние операции пользователей.')}
    <div class="table-wrap"><table class="table"><thead><tr><th>Дата</th><th>Действие</th><th>Детали</th></tr></thead><tbody>${rows.map(l=>`<tr><td>${l.created_at}</td><td>${escapeHtml(l.action)}</td><td>${escapeHtml(l.details||'')}</td></tr>`).join('')}</tbody></table></div>`;
}

init();

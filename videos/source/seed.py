"""Video uchun NAMUNAVIY e’lonlar (videoda “Namunaviy e’lonlar” deb belgilanadi). Real API orqali yaratiladi va tasdiqlanadi."""
import httpx
API = 'http://127.0.0.1:8000/api/v1'
FX = '/home/claude/TalabaGo/e2e/fixtures'
c = httpx.Client(timeout=30)
def reg(role, phone, first, **kw):
    r = c.post(API + '/auth/register', json={'role': role, 'firstName': first, 'phone': phone, 'password': 'namuna-12345', **kw}); r.raise_for_status()
    return {'Authorization': 'Bearer ' + r.json()['token']}
emp = reg('employer', '900000101', 'Namuna', company='Shahar kafesi')
land = reg('landlord', '900000102', 'Namuna')
J = [
  dict(title='Kafe ofitsianti', company='Shahar kafesi', district='Chilonzor', format='offline', type='hourly', salary=25000, salaryPeriod='hour', workTime='evening', schedule='18:00–23:00', category='Xizmat ko‘rsatish',
       description='Kechki smenada mehmonlarga xizmat ko‘rsatish. Tajriba shart emas — o‘rgatamiz.', requirements=['Xushmuomalalik', 'Haftasiga kamida 3 kun']),
  dict(title='SMM yordamchisi', company='Onlayn do‘kon', district=None, format='online', type='permanent', salary=3000000, salaryPeriod='month', workTime='flexible', schedule='Moslashuvchan', category='Marketing',
       description='Instagram va Telegram sahifalari uchun post va storylar tayyorlash, masofadan ishlash.', requirements=['Canva', 'Kreativlik']),
  dict(title='Velokuryer', company='Yetkazib berish xizmati', district='Yunusobod', format='offline', type='daily', salary=180000, salaryPeriod='day', workTime='weekend', schedule='Dam olish kunlari', category='Yetkazib berish',
       description='Dam olish kunlari buyurtmalarni velosipedda yetkazish. Velosiped beriladi.', requirements=['Jismoniy faollik']),
  dict(title='Ingliz tili o‘qituvchisi yordamchisi', company='Til o‘quv markazi', district='Mirzo Ulug‘bek', format='offline', type='hourly', salary=40000, salaryPeriod='hour', workTime='day', schedule='14:00–18:00', category='Ta’lim',
       description='Bolalar guruhlarida o‘qituvchiga yordam berish, uy vazifalarini tekshirish.', requirements=['Ingliz tili B2']),
]
def upload(h, name):
    with open(f'{FX}/{name}', 'rb') as f:
        r = c.post(API + '/files', headers=h, files={'file': (name, f, 'image/webp')}, data={'kind': 'photo'}); r.raise_for_status(); return r.json()['url']
H = [
  dict(title='Talabalar uchun 2 xonali kvartira', type='flat', district='Chilonzor', address='Chilonzor, metro yaqinida', rooms=2, area=54, price=3500000, audience='any', capacity=3, freeSpots=2,
       amenities=['Wi-Fi', 'Mebel', 'Konditsioner', 'Kir yuvish mashinasi'], description='Metroga 5 daqiqa. To‘liq jihozlangan, talabalar uchun qulay kvartira.', photos=['p01.webp', 'p02.webp', 'p03.webp', 'p04.webp']),
  dict(title='Qizlar uchun alohida xona', type='room', district='Yunusobod', address='Yunusobod, 4-mavze', rooms=1, area=16, price=1200000, audience='female', capacity=1, freeSpots=1,
       amenities=['Wi-Fi', 'Mebel', 'Isitish'], description='Toza va tinch xona, universitetga avtobusda 15 daqiqa.', photos=['p03.webp', 'p05.webp', 'p02.webp']),
  dict(title='Yotoqxonada joy', type='dorm', district='Olmazor', address='Olmazor, universitet yonida', rooms=1, area=20, price=800000, audience='male', capacity=4, freeSpots=2,
       amenities=['Wi-Fi', 'Oshxona', 'Qo‘riqlash'], description='Universitetga piyoda 5 daqiqa, oshxona va qo‘riqlash bor.', photos=['p05.webp', 'p04.webp', 'p01.webp']),
]
a = httpx.Client(timeout=30, headers={'X-Requested-With': 'TalabaGo'})
a.post(API + '/auth/admin/login', json={'username': 'videoadmin', 'password': 'video-admin-123'}).raise_for_status()
for j in J:
    r = c.post(API + '/employer/jobs', headers=emp, json=j); r.raise_for_status(); a.post(API + f'/crm/jobs/{r.json()["id"]}/approve').raise_for_status()
for h in reversed(H):
    h = dict(h); h['photos'] = [upload(land, p) for p in h['photos']]
    r = c.post(API + '/landlord/houses', headers=land, json=h); r.raise_for_status(); a.post(API + f'/crm/houses/{r.json()["id"]}/approve').raise_for_status()
print('jobs', len(c.get(API + '/jobs', headers=emp).json()), 'houses', len(c.get(API + '/houses', headers=emp).json()))

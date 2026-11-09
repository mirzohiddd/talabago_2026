"""Namuna ish beruvchi arizani “Suhbatga chaqirish”, namuna uy egasi so‘rovni “Ko‘rildi” qiladi — haqiqiy API orqali."""
import httpx
API = 'http://127.0.0.1:8000/api/v1'
c = httpx.Client(timeout=20)
def login(phone):
    return {'Authorization': 'Bearer ' + c.post(API + '/auth/login', json={'phone': phone, 'password': 'namuna-12345'}).json()['token']}
emp, land = login('900000101'), login('900000102')
for a in c.get(API + '/employer/applications', headers=emp).json():
    c.patch(API + f'/employer/applications/{a["id"]}', headers=emp, json={'status': 'viewed'})
    c.patch(API + f'/employer/applications/{a["id"]}', headers=emp, json={'status': 'interview', 'interviewAt': '2026-11-12T10:00:00+05:00'})
for r in c.get(API + '/landlord/requests', headers=land).json():
    c.patch(API + f'/landlord/requests/{r["id"]}', headers=land, json={'status': 'viewed'})
print('statuslar yangilandi')

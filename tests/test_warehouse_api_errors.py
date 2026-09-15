import re
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.warehouse_api_errors import install_error_handler


def test_unexpected_errors_are_json_and_have_private_traceback(tmp_path):
    app=FastAPI();path=tmp_path/'errors.log';install_error_handler(app,path)
    @app.get('/warehouse-assistant/api/example')
    def broken():raise RuntimeError('private diagnostic detail')
    @app.get('/warehouse-assistant/api/protected')
    def protected():raise HTTPException(401,'Login required')
    with TestClient(app,raise_server_exceptions=False) as client:
        response=client.get('/warehouse-assistant/api/example')
        assert response.status_code==500
        assert response.headers['content-type']=='application/json'
        assert 'private diagnostic detail' not in response.text
        reference=re.search(r'[a-f0-9]{12}',response.json()['detail']).group()
        trace=path.read_text(encoding='utf-8')
        assert reference in trace and 'RuntimeError: private diagnostic detail' in trace
        auth=client.get('/warehouse-assistant/api/protected')
        assert auth.status_code==401 and auth.json()=={'detail':'Login required'}

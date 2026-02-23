## Aplicação de conexão e geração de SQL DELETE

### Como rodar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Acesse:
- `http://localhost:5000/connect` para testar e salvar conexão.
- `http://localhost:5000/cleanup` para selecionar tabela, informar CNPJ e gerar SQL de DELETE por `user_id`.

### Observação
As credenciais salvas ficam em `db_config.json` (arquivo local, não versionado).

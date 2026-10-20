# Conversor de GIF para MP4

Aplicativo desktop para selecionar vários GIFs e convertê-los em paralelo para MP4.
O projeto separa a interface, a coordenação do lote e a conversão com FFmpeg para
facilitar manutenção e testes.

## Requisitos

- Python 3.10 ou superior
- Tkinter (incluído na instalação padrão do Python para Windows)

O executável do FFmpeg é fornecido pela dependência `imageio-ffmpeg`.

## Instalação e execução

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Na janela, adicione os GIFs, escolha uma pasta de saída e clique em **Converter**.
São usados até dois conversores simultaneamente. Arquivos MP4 já existentes são
ignorados por padrão; marque a opção de sobrescrita para substituí-los.

Se dois GIFs tiverem o mesmo nome, o segundo recebe um sufixo numérico no MP4
gerado para evitar colisões na pasta de saída.

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

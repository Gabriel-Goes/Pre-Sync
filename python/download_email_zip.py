import os
import re
from imapclient import IMAPClient
import pyzmail

EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')
# IMAP_SERVER = 'imap-mail.outlook.com'
IMAP_SERVER = 'outlook.office365.com'
PASTA_DOWNLOAD = '/home/ipt/projetos/QA_SISMO/'
REMETENTE_ESPERADO = 'mafioletti@jcmconsultoria.com'
PADRAO_ARQUIVO_CORRETO = r'.*\.zip$'  # r'.*\rar$'

os.makedirs(PASTA_DOWNLOAD, exist_ok=True)

with IMAPClient(IMAP_SERVER, ssl=True) as server:
    server.login(EMAIL, PASSWORD)
    server.select_folder('INBOX', readonly=True)
    uids = server.search(['FROM', REMETENTE_ESPERADO])
    print(f'Encontrados {len(uids)} e-mails de {REMETENTE_ESPERADO}')

    for uid in uids:
        raw_msg = server.fetch(uid, ['BODY[]'])
        message = pyzmail.PyzMessage.factory(raw_msg[uid][b'BODY[]'])

        if message.get_subject():
            print(f'Lendo e-mail com assunto: {message.get_subject()}')

        # Checar todos anexos
        for part in message.mailparts:
            filename = part.filename
            if filename and re.match(PADRAO_ARQUIVO_CORRETO, filename):
                file_path = os.path.join(PASTA_DOWNLOAD, filename)
                with open(file_path, 'wb') as f:
                    f.write(part.get_payload())
                print(f'Arquivo salvo em: {file_path}')

print("Processo concluído.")

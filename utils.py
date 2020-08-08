def copy_sheet_into(gc, file_id, title, folder_id, copy_permissions=False):
    from gspread.urls import DRIVE_FILES_API_V3_URL
    url = '{0}/{1}/copy'.format(DRIVE_FILES_API_V3_URL, file_id)

    payload = {
        'name': title,
        'mimeType': 'application/vnd.google-apps.spreadsheet',
    }

    if folder_id is not None:
        payload['parents'] = [folder_id]

    params = {'supportsAllDrives': True}
    r = gc.request('post', url, json=payload, params=params)
    spreadsheet_id = r.json()['id']

    new_spreadsheet = gc.open_by_key(spreadsheet_id)

    if copy_permissions:
        original = gc.open_by_key(file_id)

        permissions = original.list_permissions()
        for p in permissions:
            if p.get('deleted'):
                continue
            try:
                new_spreadsheet.share(
                    value=p['emailAddress'],
                    perm_type=p['type'],
                    role=p['role'],
                    notify=False,
                )
            except Exception:
                pass

    return new_spreadsheet


def censor_email(email):
    at = email.find("@")
    account = email[:at]
    domain = email[at:]
    if (len(account)) > 2:
        prefix = account[0]
        suffix = account[-1]
        return prefix + "*" * (len(account) - 2) + suffix + domain

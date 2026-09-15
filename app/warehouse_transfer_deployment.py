"""Warehouse-only, non-secret opt-in for the already authorized bridge account.

No environment mutation or credential persistence. SQL still enforces the
login/route policy; this profile never grants privileges or posts a document.
"""
from dataclasses import replace
import json
import logging
from pathlib import Path
from app.config import ROOT_DIR

PROFILE_PATH = ROOT_DIR / 'data' / 'warehouse-transfer-deployment.json'
FIELDS = {'version','enabled','commit_enabled','credential_source',
          'expected_server','expected_database','expected_username'}


def _disabled(settings):
    return replace(settings,varanegar_transfer_bridge_enabled=False,
        varanegar_transfer_commit_enabled=False,varanegar_transfer_sql_server='',
        varanegar_transfer_sql_database='',varanegar_transfer_sql_username='',
        varanegar_transfer_sql_password='')


def configure_transfer_bridge(settings, path: Path = PROFILE_PATH):
    try:
        raw=path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return settings
    except OSError:
        logging.getLogger(__name__).warning('Transfer deployment profile unavailable; bridge disabled.')
        return _disabled(settings)
    try:
        profile=json.loads(raw)
        if not isinstance(profile,dict) or set(profile)!=FIELDS:
            raise ValueError
        if type(profile['version']) is not int or profile['version']!=1:
            raise ValueError
        if any(type(profile[k]) is not bool for k in ('enabled','commit_enabled')):
            raise ValueError
        if profile['commit_enabled'] and not profile['enabled']:
            raise ValueError
        if profile['credential_source']!='existing_receipt_bridge':
            raise ValueError
        values={k:getattr(settings,'varanegar_receipt_sql_'+k,'')
                for k in ('server','database','username','password')}
        for key in ('server','database','username'):
            if not isinstance(profile['expected_'+key],str) or not values[key] or values[key]!=profile['expected_'+key]:
                raise ValueError
        if not values['password']:
            raise ValueError
        if not profile['enabled']:
            return _disabled(settings)
        return replace(settings,varanegar_transfer_bridge_enabled=True,
            varanegar_transfer_commit_enabled=profile['commit_enabled'],
            **{'varanegar_transfer_sql_'+key:value for key,value in values.items()})
    except (ValueError,TypeError,KeyError):
        # Never include the file contents, settings object or exception text.
        logging.getLogger(__name__).warning('Transfer deployment profile invalid; bridge disabled.')
        return _disabled(settings)

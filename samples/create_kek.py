"""
*===================================================================
*
* Licensed Materials - Property of IBM
* IBM Cloud HPC Cluster
* Copyright IBM Corporation 2019. All Rights Reserved.
* US Government Users Restricted Rights - Use, duplication or disclosure
* restricted by GSA ADP Schedule Contract with IBM Corp.
*
*===================================================================
"""

import sys
import getopt
from pycryptoki.default_templates import CKM_AES_KEY_GEN_TEMP
from pycryptoki.defines import CKM_AES_KEY_GEN, CKA_LABEL
from pycryptoki.key_generator import c_generate_key_ex
from pycryptoki.session_management import c_initialize_ex, c_open_session_ex,\
                                          login_ex, c_logout_ex, c_close_session_ex,\
                                          c_finalize_ex


def generate_keys(password, kek_plain_text):
    '''
    Generate AES keys
    password - string CryptoOfficer role password
    kek_plain_text - kek label
    '''

    # HSM slot id for HA
    slot_id = 5

    c_initialize_ex()
    auth_session = c_open_session_ex(slot_id)
    login_ex(auth_session, slot_id, password)

    CKM_AES_KEY_GEN_TEMP[CKA_LABEL] = bytes(kek_plain_text, 'utf-8')
    key_handle = c_generate_key_ex(auth_session, CKM_AES_KEY_GEN, CKM_AES_KEY_GEN_TEMP)

    c_logout_ex(auth_session)
    c_close_session_ex(auth_session)
    c_finalize_ex()

    return key_handle


def main(argv):
    co_password = ''
    plain_text = ''
    try:
        opts, _ = getopt.getopt(argv, "hc:p:", ["co_pass=", "plain_text="])
    except getopt.GetoptError:
        print('create_kek.py -c <co_password> -p <kek_label>')
        sys.exit(2)
    if not opts:
        print('create_kek.py -c <co_password> -p <kek_label>')
        sys.exit(2)
    if len(opts) != 2 or '-h' in opts:
        print('create_kek.py -c <co_password> -p <kek_label>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('create_kek.py -c <co_password> -p <kek_label>')
            sys.exit()
        elif opt in ("-c", "--co_pass"):
            co_password = arg
        elif opt in ("-p", "--kek_label"):
            plain_text = arg

    generate_keys(co_password, plain_text)


if __name__ == "__main__":
    main(sys.argv[1:])

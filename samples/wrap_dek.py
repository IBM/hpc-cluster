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

import array
import base64
import getopt
import sys
import os
import traceback
from pycryptoki.defines import CKM_AES_GCM, CKU_CRYPTO_USER, CKA_KEY_TYPE, CKK_AES,\
                               CKA_LABEL
from pycryptoki.object_attr_lookup import c_find_objects_ex
from pycryptoki.session_management import c_initialize_ex, c_open_session_ex,\
                                          login_ex, c_logout_ex, c_close_session_ex,\
                                          c_finalize_ex
from pycryptoki.mechanism import Mechanism
from pycryptoki.encryption import c_encrypt_ex
from pycryptoki.exceptions import LunaCallException


def _initialize():
    try:
        c_initialize_ex()
    except LunaCallException as lce:
        if "CKR_CRYPTOKI_ALREADY_INITIALIZED" in str(lce):
            pass


def encrypt(password, kek_label, plaintext_path):
    '''
        Encrypt plain text to cipher text
        password - string CryptoUser role password
        kek_label - string label of decryption key in HSM
        plaintext_path - path of base64 encoded data to be encrypted
    '''
    plaintext = open(plaintext_path, 'rb').read()
    encrypted = None
    i = 0
    while i < 2:
        try:
            auth_session = None
            _initialize()
            auth_session = c_open_session_ex(i)
            login_ex(auth_session, i, password, CKU_CRYPTO_USER)

            kek_handle = None
            kek_handle = c_find_objects_ex(auth_session,
                                           {CKA_KEY_TYPE: CKK_AES, CKA_LABEL: kek_label},
                                           1)
            if kek_handle:
                params = {"iv": list(range(16)), "AAD": [], "ulTagBits": 128}
                mechanism = Mechanism(mech_type=CKM_AES_GCM, params=params)
                encrypted = c_encrypt_ex(auth_session, kek_handle[0], plaintext, mechanism)
                encrypted = array.array('B', list(range(16))).tostring() + encrypted
                break
            else:
                i += 1
        except LunaCallException:
            print("Exception running key mgmt operation on slot " + str(i))
            print(traceback.format_exc())
            i += 1
        finally:
            if auth_session:
                c_logout_ex(auth_session)
                c_close_session_ex(auth_session)
            c_finalize_ex()

    if encrypted:
        ciphertext = base64.b64encode(encrypted)
        return ciphertext
    else:
        raise Exception("Failed to encrypt DEK")


def main(argv):
    co_password = ''
    kek_label = ''
    plain_text_dir = ''
    key_name = 'root.kek'
    try:
        opts, _ = getopt.getopt(argv, "hc:k:p:")
    except getopt.GetoptError:
        print('wrap_dek.py -c <cu_password> -k <kek_label> -p <dek_file_path>')
        sys.exit(2)
    if not opts:
        print('wrap_dek.py -c <cu_password> -k <kek_label> -p <dek_file_path>')
        sys.exit(2)
    if len(opts) != 3 or '-h' in opts:
        print('wrap_dek.py -c <cu_password> -k <kek_label> -p <dek_file_path>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('wrap_dek.py -c <cu_password> -k <kek_label> -p <dek_file_path>')
            sys.exit()
        elif opt == "-c":
            co_password = arg
        elif opt == "-p":
            plain_text_dir = arg
            filename = os.path.basename(plain_text_dir)
            key_name = filename.split('.')[0] + '.wdek'
        elif opt == "-k":
            kek_label = arg

    root_wdek = encrypt(co_password, kek_label, plain_text_dir)
    f = open(key_name, "wb")
    f.write(root_wdek)
    f.close()
    print("Wrapped DEK is in - %s. Upload this file to Cloud Object Storage" % key_name)


if __name__ == "__main__":
    main(sys.argv[1:])

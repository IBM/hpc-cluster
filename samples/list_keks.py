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
import getopt
import sys
import traceback

from pycryptoki.defines import CKU_CRYPTO_USER, CKA_KEY_TYPE, CKK_AES,\
                               CKA_LABEL
from pycryptoki.object_attr_lookup import c_find_objects_ex, c_get_attribute_value_ex
from pycryptoki.session_management import c_initialize_ex, c_open_session_ex,\
                                          login_ex, c_logout_ex, c_close_session_ex,\
                                          c_finalize_ex
from pycryptoki.attributes import Attributes
from pycryptoki.exceptions import LunaCallException


def _initialize():
    try:
        c_initialize_ex()
    except LunaCallException as lce:
        if "CKR_CRYPTOKI_ALREADY_INITIALIZED" in str(lce):
            pass


def list_kek_labels(password):
    '''
        List labels of upto 100 keys
        password - string CryptoUser role password
    '''

    # HSM slot id for HA
    slot_id = 5
    labels = []
    try:
        auth_session = None
        _initialize()
        auth_session = c_open_session_ex(slot_id)
        login_ex(auth_session, slot_id, password, CKU_CRYPTO_USER)

        key_handles = c_find_objects_ex(auth_session, {CKA_KEY_TYPE: CKK_AES}, 100)
        for handle in key_handles:
            label = c_get_attribute_value_ex(auth_session, handle,
                                             Attributes({CKA_LABEL: b'01234567890123456789012345'}))
            labels.append(label[3].decode("utf-8"))
    except LunaCallException:
        print("Exception running key mgmt operation")
        print(traceback.format_exc())
        raise Exception('Exception running key mgmt operation')
    finally:
        if auth_session:
            c_logout_ex(auth_session)
            c_close_session_ex(auth_session)
        c_finalize_ex()

    return labels


def main(argv):
    cu_password = ''
    try:
        opts, _ = getopt.getopt(argv, "hc:")
    except getopt.GetoptError:
        print('list_keks.py -c <cu_password>')
        sys.exit(2)
    if not opts:
        print('list_keks.py -c <cu_password>')
        sys.exit(2)
    if len(opts) != 1 or '-h' in opts:
        print('list_keks.py -c <cu_password>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('list_keks.py -c <cu_password>')
            sys.exit()
        elif opt == "-c":
            cu_password = arg
    print(list_kek_labels(cu_password))


if __name__ == "__main__":
    main(sys.argv[1:])

import base64
import sys
import os
import getopt


from pycryptoki.defines import CKM_AES_GCM, CKU_CRYPTO_USER, CKA_KEY_TYPE, CKK_AES,\
                               CKA_LABEL
from pycryptoki.object_attr_lookup import c_find_objects_ex
from pycryptoki.session_management import c_initialize_ex, c_open_session_ex,\
                                          login_ex, c_logout_ex, c_close_session_ex,\
                                          c_finalize_ex
from pycryptoki.mechanism import Mechanism
from pycryptoki.encryption import c_decrypt_ex
from pycryptoki.exceptions import LunaCallException


def _initialize():
    try:
        c_initialize_ex()
    except LunaCallException as lce:
        if "CKR_CRYPTOKI_ALREADY_INITIALIZED" in str(lce):
            pass


def decrypt(password, kek_label, path_to_plain_text):
    '''
        Decrypt cipher text to plain text
        password - string CryptoUser role password
        kek_label - string label of decryption key in HSM
        path_to_plain_text - path of base64 encoded data to be decrypted
    '''
    ciphertext = open(path_to_plain_text, 'rb').read()
    decrypted = None
    i = 0
    while i < 2:
        try:
            cipher = base64.b64decode(ciphertext)
            auth_session = None
            _initialize()
            auth_session = c_open_session_ex(i)
            login_ex(auth_session, i, password, CKU_CRYPTO_USER)

            kek_handle = None
            kek_handle = c_find_objects_ex(auth_session,
                                           {CKA_KEY_TYPE: CKK_AES, CKA_LABEL: kek_label},
                                           1)
            if kek_handle:
                params = {"iv": cipher[:16], "AAD": [], "ulTagBits": 128}
                mechanism = Mechanism(mech_type=CKM_AES_GCM, params=params)
                decrypted = c_decrypt_ex(auth_session, kek_handle[0], cipher[16:], mechanism)
                break
            else:
                i += 1
        except LunaCallException:
            i += 1
        except Exception:
            raise("Failed to decrypt DEK")
        finally:
            if auth_session:
                c_logout_ex(auth_session)
                c_close_session_ex(auth_session)
            c_finalize_ex()

    if decrypted:
        return base64.b64encode(decrypted)
    else:
        raise Exception("Failed to decrypt DEK")


def main(argv):
    co_password = ''
    kek_label = ''
    path_to_wdek = ''
    key_name = 'root.kek'
    try:
        opts, _ = getopt.getopt(argv, "hc:k:p:")
    except getopt.GetoptError:
        print('unwrap_dek.py -c <cu_password> -k <kek_label> -p <wdek_file_path>')
        sys.exit(2)
    if len(opts) != 3 or '-h' in opts:
        print('unwrap_dek.py -c <cu_password> -k <kek_label> -p <wdek_file_path>')
        sys.exit(2)
    if not opts:
        print('unwrap_dek.py -c <cu_password> -k <kek_label> -p <wdek_file_path>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('unwrap_dek.py -c <cu_password> -k <kek_label> -p <wdek_file_path>')
            sys.exit()
        elif opt == "-c":
            co_password = arg
        elif opt == "-p":
            path_to_wdek = arg
            filename = os.path.basename(path_to_wdek)
            key_name = "unwrapped_" + filename.split('.')[0] + '.dek'
        elif opt == "-k":
            kek_label = arg

    root_wdek = decrypt(co_password, kek_label, path_to_wdek)
    f = open(key_name, "wb")
    f.write(root_wdek)
    f.close()
    print("Unwrapped DEK is in %s" % key_name)


if __name__ == "__main__":
    main(sys.argv[1:])

import io
import time
import datetime
from zipfile import ZipFile

import xmltodict
import hashlib

from signxml import XMLVerifier, InvalidSignature
from lib.utils import logger



#####################################################################################################################
#
#                        |/|###################################|/|
#                        |/|    [ Steps to verify signature ]  |/|
#                        |/|###################################|/|
#
# https://uidai.gov.in/images/Offline-Aadhaar-Data-Verification-Service_v1-23082018.pdf
# https://uidai.gov.in/ecosystem/authentication-devices-documents/about-aadhaar-paperless-offline-e-kyc.html
#
#
# Steps to validate signature :

# 1. Read the entire XML.

# 2. Get signature from xml

# 3. Get Certificate from here(https://uidai.gov.in/images/authDoc/uidai_offline_publickey_19062019.cer).

# 4. If you have downloaded Offline XML before 18 Jun 2019. then get Certificate from
# here(https://uidai.gov.in/images/uidai_offline_publickey_29032019.cer)

# 5. If you have downloaded the client before 28 March, then get Certificate from
# here(https://uidai.gov.in/images/uidai_offline_publickey_26022019.cer).

# 6. Convert certificate to base64 string.

# 7. Sample code snippets provided
# here(https://uidai.gov.in/ecosystem/authentication-devices-documents/developer-section/915-developer-section/tutorial-section.html).
#


def verify_sign(public_key_loc, signature, data):
    '''
    Verifies with a public key from whom the data came that it was indeed
    signed by their private key
    param: public_key_loc Path to public key
    param: signature String signature to be verified
    return: Boolean. True if the signature is valid; False otherwise.
    '''

    cert = ''
    with open('lib/uidai_certificate/uidai_offline_publickey_19062019.cer', 'r') as f:
        cert = f.read()
    try:
        XMLVerifier().verify(data=data, x509_cert=cert, expect_references=1)
        return True
    except InvalidSignature as ex:
        raise InvalidSignature
    except Exception as ex:
        logger.exception(ex)
    return False


def get_user_kyc_data(zip_file_loc, share_code, email='', phone_no=''):
    xml_file_data = ''

    with ZipFile(zip_file_loc) as zf:
        info = [file for file in zf.infolist()]
        for fl in info:
            xml_file_data = zf.open(fl.filename , pwd=bytes(str(share_code).encode())).read()
            logger.debug('done.....')

    xmlDoc = xml_file_data
    logger.debug('got xml data....')
    root = (xmltodict.parse(xmlDoc))
    kycroot = root['OfflinePaperlessKyc']
    uid_data = kycroot['UidData']
    poi = uid_data['Poi']
    pht = uid_data['Pht']
    poa = uid_data['Poa']
    signature = kycroot['Signature']['SignatureValue']

    # Attribute
    #
    # * Normal  - n(Name), g(Gender), a(Address), d(Date of birth), r(aadhar + timestamp), v(XML version)
    # * Encrypt - e(Email), m(Mobile no), s(Signeture), i(Image)

    json_dict = dict()
    personal_data = dict()

    ### Name
    personal_data['name'] = poi['@name']  # Tr.get('n')

    # ### Gender
    personal_data['gender'] = poi['@gender']  # Tr.get('g')

    # ### Date of birth
    s = poi['@dob'] or ''

    try:
        dob = datetime.datetime.strptime(s, "%d-%m-%Y").strftime('%Y-%m-%d')
        personal_data['dob'] = dob
    except:
        personal_data['dob'] = s

    # ### Address
    address_info_list = ['@careof', '@house', '@landmark', '@loc', '@vtc', '@subdist', '@dist', '@state', '@country']
    personal_data['address'] = ','.join([poa[adr] for adr in address_info_list if poa.get(adr)])
    #",".join(["%s:%s" % (k.replace('@',''), v) for k, v in poa.items()])

    ### Image
    reference_id = kycroot['@referenceId']
    personal_data['reference_id'] = reference_id

    personal_data['image'] = F"data:image/png;base64, {pht}"

    json_dict['personal_data'] = personal_data

    # ### Last 4 digit Aadhar


    #json_dict['Aadhaar_last_4digit'] = 'XXXX-XXXX-' + reference_id


    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    json_dict['timestamp'] = st
    validation_dic = dict()

    # ### Email
    #
    # Logic - Sha256(Sha256(Email+SharePhrase))*number of times last digit of Aadhaar number

    def Secure(value, sharecode, laadhar, string):

        value = value + sharecode
        if laadhar == 0:
            laadhar = 1

        for x in range(0, laadhar):
            value = hashlib.sha256(value.encode('utf-8')).hexdigest()
        if string == value:
            return "Valid"
        else:
            return "Invalid"

    mailstr = poi['@e']

    is_valid_mail = Secure(email, str(share_code), int(reference_id[:4][-1]), mailstr)
    validation_dic['email'] = is_valid_mail
    mobile_str = poi['@m']

    is_valid_phone = Secure(phone_no, str(share_code), int(reference_id[:4][-1]), mobile_str)
    validation_dic['phone'] = is_valid_phone

    is_valid_signeture = verify_sign('/home/shivansh/Desktop/uidai_offline_publickey_19062019.cer',
                                     signature, xml_file_data)

    validation_dic['digital_signeture'] = is_valid_signeture

    validation_dic['status'] = 'y'
    validation_dic['Description'] = 'Authenticated Successfully'

    if ((is_valid_mail == 'Invalid' and is_valid_phone == 'Invalid') or is_valid_signeture == 'Invalid'):
        validation_dic['status'] = 'n'
        validation_dic['Description'] = 'Authentication Failed'

    json_dict['validation'] = validation_dic

    return json_dict, xml_file_data

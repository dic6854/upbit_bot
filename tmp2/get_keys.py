import os

def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']

    return access_key, secret_key


if __name__ == "__main__":
    myAccess, mySecret = get_keys()

    print(f"My Access Kery : {myAccess}")
    print(f"My Secret Kery : {mySecret}")
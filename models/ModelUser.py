from .entities.User import User

class ModelUser():

    def login(self, db, user):
        try:
            cursor=db.connection.cursor()
            sql="""SELECT user_id, username, password, fullname FROM users
                    WHERE username = '{}'""".format(user.username)
            cursor.execute(sql)
            row = cursor.fetchone()
            if row != None:
                user =User(row[0], row[1], User.check_password(row[2], user.password), row[3])
                return user
            else:
                return None
        except Exception as ex:
            raise Exception(ex)

    def get_by_id(self, db, user_id):
        try:
            cursor=db.connection.cursor()
            sql="SELECT user_id, username, fullname FROM users WHERE user_id = {}".format(user_id)
            cursor.execute(sql)
            row = cursor.fetchone()
            if row != None:
                logged_user =User(row[0], row[1], None, row[2])
                return logged_user
            else:
                return None
        except Exception as ex:
            raise Exception(ex)
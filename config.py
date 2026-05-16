class Config:
    SECRET_KEY = 'dev-secret-key-123'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:Cex060214@localhost/pet_hospital?charset=utf8mb4'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
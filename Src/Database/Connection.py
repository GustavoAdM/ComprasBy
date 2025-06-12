import pandas as pd
import configparser
import logging
from firebird.driver import driver_config, connect
from contextlib import contextmanager

class FirebirdDB:
    def __init__(self, config_file='Config\\Config.ini'):
        # Leitura do arquivo de configuração
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        # Atribuindo os parâmetros de configuração
        self.usuario = self.config.get('database', 'usuario', fallback=None)
        self.senha = self.config.get('database', 'senha', fallback=None)
        self.ip = self.config.get('database', 'ip', fallback=None)
        self.caminho = self.config.get('database', 'caminho', fallback=None)
        self.porta = self.config.getint('database', 'porta', fallback="3050")
        self.lib_path = self.config.get('database', 'lib_path', fallback=None)

        #Configurando conexão do Firebird
        driver_config.server_defaults.host.value = str(self.ip)
        driver_config.server_defaults.port.value = str(self.porta)
        driver_config.server_defaults.user.value = str(self.usuario)
        driver_config.server_defaults.password.value = str(self.senha)
        driver_config.fb_client_library.value = self.lib_path
        driver_config.db_defaults.charset.value = 'ISO8859_1'

        # Inicialização da conexão
        self.connection = None

        # Configuração do logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Verifica se as configurações necessárias estão presentes
        self._validate_config()

    def _validate_config(self):
        """Valida se todas as configurações necessárias estão presentes"""
        if not all([self.usuario, self.senha, self.ip, self.caminho]):
            raise ValueError("Parâmetros de conexão incompletos no arquivo de configuração.")

    def connect(self):
        """Estabelece a conexão com o banco de dados Firebird"""
        if self.connection:
            self.logger.warning("Já há uma conexão ativa.")
            return

        try:
            # Estabelece a conexão
            self.connection = connect(self.caminho)
        except Exception as e:
            self.logger.error(f"Erro ao conectar ao banco de dados: {e}")
            self.connection = None

    def disconnect(self):
        """Fecha a conexão com o banco de dados"""
        if self.connection:
            try:
                self.connection.close()
                self.logger.info("Conexão encerrada.")
            except Exception as e:
                self.logger.error(f"Erro ao fechar a conexão: {e}")
            finally:
                self.connection = None

    @contextmanager
    def session_scope(self):
        """Context manager para gerenciar a sessão de conexão"""
        if not self.connection:
            self.connect()

        try:
            yield self.connection  # Retorna a conexão para ser utilizada no pandas.read_sql
        except Exception as e:
            self.logger.error(f"Erro durante a execução da consulta: {e}")
            if self.connection:
                self.connection.rollback()
            raise
        finally:
            if self.connection:
                self.connection.commit()

    def read_sql(self, query):
        """Executa uma consulta SQL e retorna os resultados em um DataFrame pandas"""
        if not self.connection:
            self.connect()

        try:
            # Usando pandas.read_sql para executar a consulta e retornar um DataFrame
            df = pd.read_sql(query, self.connection)
            #self.logger.info("Consulta executada com sucesso.")
            return df
        except Exception as e:
            self.logger.error(f"Erro ao ler a consulta SQL com pandas: {e}")
            return None
        
    def execute_UDI(self, query):
        """Executa uma consulta de inserção, atualização ou exclusão"""
        with self.connection.cursor() as cursor:
            try:
                cursor.execute(query)
                cursor.connection.commit()  # Confirma a transação usando o commit da conexão
            except Exception as e:
                self.logger.error(f"Erro ao executar a consulta de UDI: {e}")
                cursor.connection.rollback()  # Faz rollback caso ocorra erro
                return e

db = FirebirdDB()
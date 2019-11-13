import time
import psycopg2
from configs import *
import hashlib
from psycopg2 import sql
import psycopg2.extras

# helpful query: select id, cid1 is null as cid1_is_null, cid2 is null as cid2_is_null from cnf_1560847944_097688;

class DbAdapter:


    def __init__(self):
        self.conn_string = "host={} port={} dbname={} user={} password={}".format(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
        self.conn = None
        self.cur = None
        
        try:
            # connect to the PostgreSQL server
            self.conn = psycopg2.connect(self.conn_string, cursor_factory=psycopg2.extras.DictCursor)
            self.cur = self.conn.cursor()
            
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))

    def __del__(self):
        try:
            # close communication with the PostgreSQL database server
            self.cur.close()
            # commit the changes
            self.conn.commit()
            # close the connection
            if self.conn is not None:
                self.conn.close()
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))

    ### GlobalSetsTable methods ###
    
    def gs_create_table(self, table_name):
        """ create tables in the PostgreSQL database"""
        table_command = """
                CREATE TABLE IF NOT EXISTS {0} (
                hash BYTEA PRIMARY KEY,
                body TEXT,
                cid1 BYTEA,
                cid2 BYTEA,
                mapping INTEGER[],                
                num_of_clauses INTEGER DEFAULT 0,
                num_of_vars INTEGER DEFAULT 0,
                unique_nodes INTEGER DEFAULT 0,
                redundant_nodes INTEGER DEFAULT 0,
                redundant_hits INTEGER DEFAULT 0,
                redundant_times INTEGER DEFAULT 0,
                date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(hash)
            )
            """.format(table_name)
        # redundant_nodes field counts how many redundant nodes in this set's subgraph.
        # redundant_hits how many redudants hits was in this set's subgraph.
        # redundant_times field counts how many times this particular set was a redundant set.
        
        # The UNIQUE constraint will prevent any other process from writing the same data, the exception should be handled then
        # be aware that creating an index on table with exaustive inserts can slow it down. Check the speed without the index and compare.
        index_commands = [
                "CREATE INDEX IF NOT EXISTS num_clauses ON {0} (num_of_clauses)".format(table_name),
                "CREATE INDEX IF NOT EXISTS num_vars ON {0} (num_of_vars)".format(table_name),
                "CREATE INDEX IF NOT EXISTS date_created ON {0} (date_created)".format(table_name),
                "CREATE INDEX IF NOT EXISTS unique_nodes ON {0} (unique_nodes)".format(table_name),
                "CREATE INDEX IF NOT EXISTS redundant_times ON {0} (redundant_times)".format(table_name)
            ]
        
        try:
            # create table 
            self.cur.execute(table_command)
            # create indeces
            for index_command in index_commands:
                self.cur.execute(index_command)
            
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))
 
 
    def gs_insert_row(self, table_name, hash, set_body, child1_hash, child2_hash, mapping, num_of_clauses, num_of_vars):

        """ insert a row item into the table """
        success = SUCCESS
        try:            
            # execute the INSERT statement
            #self.cur.execute(sql.SQL("insert into {} values (%s, %s)").format(sql.Identifier('my_table')), [10, 20])
            self.cur.execute(sql.SQL("INSERT INTO {0}(hash, body, cid1, cid2, mapping, num_of_clauses, num_of_vars) VALUES(%s, %s, %s, %s, %s, %s, %s)").format(sql.Identifier(table_name)), (hash, set_body, child1_hash, child2_hash, mapping, num_of_clauses, num_of_vars))
            self.conn.commit()
        except (Exception, psycopg2.errors.UniqueViolation) as UniqueViolationError:
            success = DB_UNIQUE_VIOLATION
            logger.debug("Node is already found in the global DB")
        except (Exception, psycopg2.DatabaseError) as error:            
            logger.error("DB Error: " + str(error))
            success = DB_UNKNOWN_ERROR
    
        return success

    def gs_does_exist(self, table_name, value):
        
        result = False
        try:
            self.cur.execute(sql.SQL("SELECT 1 FROM {0} WHERE hash = %s LIMIT 1").format(sql.Identifier(table_name)), (value, ))
            result = bool(self.cur.rowcount)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))
            result = False

        return result


    def gs_update_count(self, table_name, unique_nodes, redundant_nodes, redundant_hits, hash):
        result = False
        try:
            self.cur.execute(sql.SQL("UPDATE {0} SET unique_nodes = %s, redundant_nodes = %s, redundant_hits = %s WHERE hash = %s").format(sql.Identifier(table_name)), (unique_nodes, redundant_nodes, redundant_hits, hash))
            # get result
            result = bool(self.cur.rowcount)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))
            logger.critical("Error - {0}".format(traceback.format_exc()))
            result = False

        return result

    def gs_update_redundant_times(self, table_name, redundant_times, hash):
        result = False
        try:
            self.cur.execute(sql.SQL("UPDATE {0} SET redundant_times = redundant_times + %s WHERE hash = %s").format(sql.Identifier(table_name)), (redundant_times, hash))
            # get result
            result = bool(self.cur.rowcount)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))
            logger.critical("Error - {0}".format(traceback.format_exc()))
            result = False

        return result

    # load only solved sets (only solved sets have unique_nodes > 0)
    def gs_load_solved_sets(self, table_name, num_clauses):
        result = []
        try:
            self.cur.execute(sql.SQL("SELECT hash, unique_nodes, redundant_nodes FROM {0} WHERE num_of_clauses <= %s AND unique_nodes > 0").format(sql.Identifier(table_name)), (num_clauses, ))
            rows = self.cur.fetchall()
            for row in rows:
                result.append([bytes(row[0]), row[1], row[2]])

        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))

        return result

    # load only unsolved sets (only unsolved sets have unique_nodes = 0)
    def gs_load_unsolved_sets(self, table_name, num_clauses):
        result = []
        try:
            self.cur.execute(sql.SQL("SELECT hash FROM {0} WHERE num_of_clauses <= %s AND unique_nodes = 0").format(sql.Identifier(table_name)), (num_clauses, ))
            rows = self.cur.fetchall()
            for row in rows:
                result.append(bytes(row[0]))

        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))

        return result

    def gs_get_set_data(self, table_name, set_hash):
        result = {}
        try:
            self.cur.execute(sql.SQL("SELECT * FROM {0} WHERE hash = %s").format(sql.Identifier(table_name)), (set_hash, ))
            result = self.cur.fetchone()
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))

        return result

    def gs_get_children(self, table_name, set_hash):
        result = (None, None)
        try:
            self.cur.execute(sql.SQL("SELECT cid1, cid2 FROM {0} WHERE hash = %s").format(sql.Identifier(table_name)), (set_hash, ))
            row = self.cur.fetchone()
            result = (bytes(row[0]), bytes(row[1]))

        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))

        return result
    
    def gs_get_body(self, table_name, set_hash):
        result = None
        try:
            self.cur.execute(sql.SQL("SELECT body FROM {0} WHERE hash = %s").format(sql.Identifier(table_name)), (set_hash, ))
            row = self.cur.fetchone()
            result = row[0]

        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))

        return result

    ### RunTimeQueue methods ###

    def rtq_create_table(self, table_name):
        """ create tables in the PostgreSQL database"""
        table_command = """
                CREATE TABLE {0} (
                id INTEGER PRIMARY KEY,
                body TEXT
            )
            """.format(table_name)

        try:
            # create table 
            self.cur.execute(table_command)            
            self.conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))
            return False
            
        return True
 
 
    def rtq_insert_set(self, table_name, id, body):

        """ insert a new row into the table """
        success = False
        try:            
            # execute the INSERT statement
            self.cur.execute(sql.SQL("INSERT INTO {0}(id, body) VALUES(%s, %s)").format(sql.Identifier(table_name)), (id, body))            
            success = True
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))
            success = False
    
        return success

    def rtq_get_set(self, table_name, id):
        
        result = None
        try:
            self.cur.execute(sql.SQL("SELECT id, body FROM {0} WHERE id = %s LIMIT 1").format(sql.Identifier(table_name)), (id, ))
            result = self.cur.fetchone()
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))

        return result


    def rtq_cleanup(self, table_name):
        success = False
        try:
            self.cur.execute(sql.SQL("DROP table {0}").format(sql.Identifier(table_name)))
            # get result
            success = True
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("DB Error: " + str(error))

        return success


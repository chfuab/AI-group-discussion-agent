get_tables_and_columns_pg = """
                    SELECT table_name, column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                    ORDER BY table_name, ordinal_position
                """ # %s -> database_name
get_tables_and_columns_mysql = """
                    SELECT table_name, column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                    ORDER BY table_name, ordinal_position
                """ # %s -> database_name

get_relationships_pg = """
                    SELECT 
                        tc.table_name,
                        kcu.column_name,
                        ccu.table_name,
                        ccu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu
                        ON tc.constraint_name = ccu.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = %s
                """ # %s -> database_name
get_relationships_mysql = """
                    SELECT 
                        table_name,
                        column_name,
                        referenced_table_name,
                        referenced_column_name
                    FROM information_schema.key_column_usage
                    WHERE referenced_table_name IS NOT NULL
                        AND table_schema = %s
                """ # %s -> database_name
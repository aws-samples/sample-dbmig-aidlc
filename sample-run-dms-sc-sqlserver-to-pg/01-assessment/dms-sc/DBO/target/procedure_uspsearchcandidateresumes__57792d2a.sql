CREATE OR REPLACE PROCEDURE adventureworks_dbo.uspsearchcandidateresumes(IN par_searchstring VARCHAR, IN par_useinflectional NUMERIC DEFAULT 0, IN par_usethesaurus NUMERIC DEFAULT 0, IN par_language INTEGER DEFAULT 0, INOUT p_refcur refcursor DEFAULT NULL, INOUT p_refcur_2 refcursor DEFAULT NULL, INOUT p_refcur_3 refcursor DEFAULT NULL)
AS 
$BODY$
/* A stored procedure which demonstrates integrated full text search */
DECLARE
    var_string VARCHAR(1050);
BEGIN
    /*
    [7644 - Severity CRITICAL - PostgreSQL doesn't support the EXECUTE AS CALLER clause. Convert your source code manually.]
    EXECUTE AS CALLER
    */
    /* setting the lcid to the default instance LCID if needed */
    IF par_language = NULL OR par_language = 0 THEN
        /*
        [7811 - Severity CRITICAL - PostgreSQL doesn't support the SERVERPROPERTY(NVARCHAR) function. DMS SC skips this unsupported function in the converted code. Create a user-defined function to replace the unsupported function.]
        SELECT @language =CONVERT(int, serverproperty('lcid'))
        */
        BEGIN
        END;
    END IF;
    /* FREETEXTTABLE case as inflectional and Thesaurus were required */

    IF par_useThesaurus = 1 AND par_useInflectional = 1 THEN
        OPEN p_refcur FOR
        /*
        [9996 - Severity CRITICAL - Transformer error occurred in innerJoinTableSource. Please submit report to developers.]
        SELECT FT_TBL.[JobCandidateID], KEY_TBL.[RANK] FROM [HumanResources].[JobCandidate] AS FT_TBL
                                INNER JOIN FREETEXTTABLE([HumanResources].[JobCandidate],*, @searchString,LANGUAGE @language) AS KEY_TBL
                           ON  FT_TBL.[JobCandidateID] =KEY_TBL.[KEY]
        */
        /* >> DMS SC preserves the tuple structure of the transformed statement due to the detection of the critical Action Item >> */
        SELECT
            NULL::INTEGER AS "JOBCANDIDATEID", NULL::VARCHAR(8000) AS "KEY_TBL.[RANK]"
        /* << DMS SC preserves the tuple structure of the transformed statement due to the detection of the critical Action Item << */;
    ELSE
        IF par_useThesaurus = 1 THEN
            SELECT
                'FORMSOF(THESAURUS,"' || par_searchString || '"' || ')'
                INTO var_string;
            OPEN p_refcur_2 FOR
            /*
            [9996 - Severity CRITICAL - Transformer error occurred in innerJoinTableSource. Please submit report to developers.]
            SELECT FT_TBL.[JobCandidateID], KEY_TBL.[RANK] FROM [HumanResources].[JobCandidate] AS FT_TBL
                                    INNER JOIN CONTAINSTABLE([HumanResources].[JobCandidate],*, @string,LANGUAGE @language) AS KEY_TBL
                               ON  FT_TBL.[JobCandidateID] =KEY_TBL.[KEY]
            */
            /* >> DMS SC preserves the tuple structure of the transformed statement due to the detection of the critical Action Item >> */
            SELECT
                NULL::INTEGER AS "JOBCANDIDATEID", NULL::VARCHAR(8000) AS "KEY_TBL.[RANK]1"
            /* << DMS SC preserves the tuple structure of the transformed statement due to the detection of the critical Action Item << */;
        ELSE
            IF par_useInflectional = 1 THEN
                SELECT
                    'FORMSOF(INFLECTIONAL,"' || par_searchString || '"' || ')'
                    INTO var_string;
                OPEN p_refcur_3 FOR
                /*
                [9996 - Severity CRITICAL - Transformer error occurred in innerJoinTableSource. Please submit report to developers.]
                SELECT FT_TBL.[JobCandidateID], KEY_TBL.[RANK] FROM [HumanResources].[JobCandidate] AS FT_TBL
                                        INNER JOIN CONTAINSTABLE([HumanResources].[JobCandidate],*, @string,LANGUAGE @language) AS KEY_TBL
                                   ON  FT_TBL.[JobCandidateID] =KEY_TBL.[KEY]
                */
                /* >> DMS SC preserves the tuple structure of the transformed statement due to the detection of the critical Action Item >> */
                SELECT
                    NULL::INTEGER AS "JOBCANDIDATEID", NULL::VARCHAR(8000) AS "KEY_TBL.[RANK]11"
                /* << DMS SC preserves the tuple structure of the transformed statement due to the detection of the critical Action Item << */;
            ELSE
                /* base case, plain CONTAINSTABLE */
                SELECT
                    '"' || par_searchString || '"'
                    INTO var_string;
                OPEN p_refcur_3 FOR
                /*
                [9996 - Severity CRITICAL - Transformer error occurred in innerJoinTableSource. Please submit report to developers.]
                SELECT FT_TBL.[JobCandidateID],KEY_TBL.[RANK] FROM [HumanResources].[JobCandidate] AS FT_TBL
                                        INNER JOIN CONTAINSTABLE([HumanResources].[JobCandidate],*,@string,LANGUAGE @language) AS KEY_TBL
                                   ON  FT_TBL.[JobCandidateID] =KEY_TBL.[KEY]
                */
                /* >> DMS SC preserves the tuple structure of the transformed statement due to the detection of the critical Action Item >> */
                SELECT
                    NULL::INTEGER AS "JOBCANDIDATEID", NULL::VARCHAR(8000) AS "KEY_TBL.[RANK]111"
                /* << DMS SC preserves the tuple structure of the transformed statement due to the detection of the critical Action Item << */;
            END IF;
        END IF;
    END IF;
END;
$BODY$
LANGUAGE plpgsql;
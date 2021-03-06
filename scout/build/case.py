import logging

from datetime import datetime

from scout.exceptions import (PedigreeError, ConfigError, IntegrityError)

from . import build_individual

log = logging.getLogger(__name__)

def build_phenotype(phenotype_id, adapter):
    """Build a small phenotype object

        Build a dictionary with phenotype_id and description

    Args:
        phenotype_id (str): The phenotype id
        adapter (scout.adapter.MongoAdapter)

    Returns:
        phenotype_obj (dict):

        dict(
            phenotype_id = str,
            feature = str, # description of phenotype
            )
    """
    phenotype_obj = {}
    phenotype = adapter.hpo_term(phenotype_id)
    if phenotype:
        phenotype_obj['phenotype_id'] = phenotype['hpo_id']
        phenotype_obj['feature'] = phenotype['description']
    return phenotype

def build_case(case_data, adapter):
    """Build a case object that is to be inserted to the database

    Args:
        case_data (dict): A dictionary with the relevant case information
        adapter (scout.adapter.MongoAdapter)

    Returns:
        case_obj (dict): A case object

    dict(
        case_id = str, # required=True, unique
        display_name = str, # If not display name use case_id
        owner = str, # required

        # These are the names of all the collaborators that are allowed to view the
        # case, including the owner
        collaborators = list, # List of institute_ids
        assignee = str, # _id of a user
        individuals = list, # list of dictionaries with individuals
        created_at = datetime,
        updated_at = datetime,
        suspects = list, # List of variants referred by there _id
        causatives = list, # List of variants referred by there _id

        synopsis = str, # The synopsis is a text blob
        status = str, # default='inactive', choices=STATUS
        is_research = bool, # default=False
        research_requested = bool, # default=False
        rerun_requested = bool, # default=False

        analysis_date = datetime,
        analysis_dates = list, # list of datetimes

        # default_panels specifies which panels that should be shown when
        # the case is opened
        panels = list, # list of dictionaries with panel information

        dynamic_gene_list = list, # List of genes

        genome_build = str, # This should be 37 or 38
        genome_version = float, # What version of the build

        rank_model_version = float,
        rank_score_threshold = int, # default=8

        phenotype_terms = list, # List of dictionaries with phenotype information
        phenotype_groups = list, # List of dictionaries with phenotype information

        madeline_info = str, # madeline info is a full xml file

        vcf_files = dict, # A dictionary with vcf files

        diagnosis_phenotypes = list, # List of references to diseases
        diagnosis_genes = list, # List of references to genes

        has_svvariants = bool, # default=False

        is_migrated = bool # default=False

    )
    """
    try:
        log.info("build case with id: {0}".format(case_data['case_id']))
        case_obj = {'_id': case_data['case_id']}
        case_obj['case_id'] = case_data['case_id']
    except KeyError as err:
        raise PedigreeError("Case has to have a case id")

    case_obj['display_name'] = case_data.get('display_name', case_obj['case_id'])

    # Check if institute exists in database
    try:
        institute_id = case_data['owner']
    except KeyError as err:
        raise ConfigError("Case has to have a institute")
    institute_obj = adapter.institute(institute_id)
    if not institute_obj:
        raise IntegrityError("Institute %s not found in database" % institute_id)
    case_obj['owner'] = case_data['owner']

    # Owner allways has to be part of collaborators
    collaborators = set(case_data.get('collaborators', []))
    collaborators.add(case_data['owner'])
    case_obj['collaborators'] = list(collaborators)

    if case_data.get('assignee'):
        case_obj['assignees'] = [case_data['assignee']]

    # Individuals
    ind_objs = []
    try:
        for individual in case_data.get('individuals', []):
            ind_objs.append(build_individual(individual))
    except Exception as error:
        ## TODO add some action here
        raise error
    # sort the samples to put the affected individual first
    sorted_inds = sorted(ind_objs, key=lambda ind: -ind['phenotype'])
    case_obj['individuals'] = sorted_inds

    now = datetime.now()
    case_obj['created_at'] = now
    case_obj['updated_at'] = now

    if case_data.get('suspects'):
        case_obj['suspects'] = case_data['suspects']
    if case_data.get('causatives'):
        case_obj['causatives'] = case_data['causatives']

    case_obj['synopsis'] = case_data.get('synopsis', '')

    case_obj['status'] = 'inactive'
    case_obj['is_research'] = False
    case_obj['research_requested'] = False
    case_obj['rerun_requested'] = False

    analysis_date = case_data.get('analysis_date')
    if analysis_date:
        case_obj['analysis_date'] = analysis_date
        case_obj['analysis_dates'] = [analysis_date]

    # We store some metadata and references about gene panels in 'panels'
    case_panels = case_data.get('gene_panels', [])
    default_panels = case_data.get('default_panels', [])
    panels = []
    
    for panel_name in case_panels:
        panel_obj = adapter.gene_panel(panel_name)
        if not panel_obj:
            raise IntegrityError("Panel %s does not exist in database" % panel_name)
        panel = {
            'panel_id': panel_obj['_id'],
            'panel_name': panel_obj['panel_name'],
            'display_name': panel_obj['display_name'],
            'version': panel_obj['version'],
            'updated_at': panel_obj['date'],
            'nr_genes': len(panel_obj['genes'])
        }
        if panel_name in default_panels:
            panel['is_default'] = True
        else:
            panel['is_default'] = False
        panels.append(panel)

    case_obj['panels'] = panels

    case_obj['dynamic_gene_list'] = {}

    # Meta data
    genome_build = case_data.get('genome_build', '37')
    if not genome_build in ['37', '38']:
        pass
        ##TODO raise exception if invalid genome build was used

    case_obj['genome_build'] = genome_build
    case_obj['genome_version'] = case_data.get('genome_version')

    if case_data.get('rank_model_version'):
        case_obj['rank_model_version'] = float(case_data['rank_model_version'])

    if case_data.get('rank_score_threshold'):
        case_obj['rank_score_threshold'] = float(case_data['rank_score_threshold'])

    # phenotype information
    phenotypes = []
    for phenotype in case_data.get('phenotype_terms', []):
        phenotype_obj = build_phenotype(phenotype, adapter)
        if phenotype_obj:
            phenotypes.append[phenotype_obj]
    if phenotypes:
        case_obj['phenotype_terms'] = phenotypes

    # phenotype groups
    phenotype_groups = []
    for phenotype in case_data.get('phenotype_groups', []):
        phenotype_obj = build_phenotype(phenotype, adapter)
        if phenotype_obj:
            phenotype_groups.append[phenotype_obj]
    if phenotype_groups:
        case_obj['phenotype_groups'] = phenotype_groups


    # Files
    case_obj['madeline_info'] = case_data.get('madeline_info')
    case_obj['vcf_files'] = case_data.get('vcf_files', {})

    case_obj['has_svvariants'] = False
    if (case_obj['vcf_files'].get('vcf_sv') or case_obj['vcf_files'].get('vcf_sv_research')):
        case_obj['has_svvariants'] = True

    case_obj['is_migrated'] = False

    return case_obj

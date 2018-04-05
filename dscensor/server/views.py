from dscensor import app, session, g, render_template, request
from flask import render_template_string, make_response, jsonify
from neo4j_db import neo4j_connection_pool as cpool
from client.templating import neo4j_dscensor_linkout, igv_template, file_listing
from api import help, derived_from, visualize_paths

logger = app.logger

@app.route('/')
def document_root():
    return render_template('index.html', static_path='/static')

#@app.route('/large_example')
#def large_example():
#    return app.large_example

#@app.route('/DSCensor_example')
#def dscensor_example():
#    return app.dscensor_example

@app.route('/DSCensor_example_wscatter')
def dscensor_example_scatter():
    return render_template(
                   'templating/templates/dscensor_fixed_scatterdraft.html',
                   static_path='/static'
          )

@app.route('/medicago_metrics')
def medicago_metrics():
    return render_template(
                   'templating/templates/medicago_assembly_metrics.html',
                   static_path='/static'
          )

@app.route('/DSCensor_neo4j')
def dscensor_neo4j():
#    response = make_response(render_template_string(app.neo4j_example))
#    response.headers['Access-Control-Allow-Origin'] =  '*'
    response = render_template('templating/templates/test_me_linkout.html',
                               static_path='/static')
    return response

@app.route('/DSCensor_neo4j_dynamic')
def dscensor_neo4j_dynamic():
#    response = make_response(render_template_string(app.neo4j_example))
    response = make_response(render_template_string(neo4j_dscensor_linkout.dscensor_neo4j_test('gff')))
#    response.headers['Access-Control-Allow-Origin'] =  '*'
#    response = render_template('templating/templates/test_me_linkout.html',
#                               static_path='/static')
    return response


@app.route('/DSCensor_neo4j_dynamic_fa')
def dscensor_neo4j_dynamic_fa():
#    response = make_response(render_template_string(app.neo4j_example))
    response = make_response(render_template_string(neo4j_dscensor_linkout.dscensor_neo4j_test('fasta')))
#    response.headers['Access-Control-Allow-Origin'] =  '*'
#    response = render_template('templating/templates/test_me_linkout.html',
#                               static_path='/static')
    return response


@app.route('/file-listing/<filetype>', methods=['GET'])
def list_files_by_type(filetype):
    '''Get all files of type "filetype"'''
    if request.method == 'GET':
        data = {'data': {}, 'error': ''}
        with cpool.get_session() as session:
            statement = 'MATCH (n:{}) return distinct n'.format(filetype)
            return_me = []
            for r in session.run(statement):
                properties = r[0].properties  # get properties of m
                filename = properties['name']
                filetype = properties['filetype']
                assert filename, 'files should have a name this one doesnt'
                assert filetype, 'files should have a type this one doesnt'
                url = properties['url']
                if not url:  # not an error, but won't return for visual
                    logger.warning('No url for {} will not return'.format(
                                                                     filename))
                    continue
                if filetype not in data['data']:
                    data['data'][filetype] = []
                data['data'][filetype].append({'filename': filename, 
                                               'url': url})
                print data
        response = make_response(render_template_string(file_listing.file_listing(data)))
        return response


@app.route('/visualize-igv/<filename>', methods=['GET'])
def visualize_igv(filename):
    '''Get data for filename's assembly to allow user to visualize all

       related data
    '''
    if request.method == 'GET':  # get fasta and then get all others
        data = {}
        visualize_me = {'selection' : filename, 'data' : data}
        msg = ''
        count = 0
        msg += 'Searching for {}'.format(filename)
        logger.debug(msg)
        with cpool.get_session() as session:  # get session from driver
            statement = 'MATCH (n {name:{filename}})-[:DERIVED_FROM*1..'
            statement += ']->(m:fasta) return distinct m'  # get files fasta
            return_me = []
            logger.debug(statement)  # if necessary
            for r in session.run(statement, {'filename' : filename}):  # run
                if count == 1:  # to report if multiple fasta are found
                    logger.warning('Multiple fasta for {}'.format(filename))
                count += 1
                logger.info(r[0].properties)  # testing
                return_me.append(r[0].properties)  # get dictionary
            if not return_me:  # if empty check to see if already fasta
                statement = 'MATCH (n:fasta {name:{filename}}) return n'
                return_me = []
                for r in session.run(statement, {'filename' : filename}):
                    return_me.append(r[0].properties)
            if not return_me:  # wasn't fasta and no fasta were found not error
                logger.error('No fasta found for {}'.format(filename))
                return jsonify(visualize_me), 200  # return empty
            fasta = return_me[0]['name']  # this is dumb fix later
            url = return_me[0]['url']
            data['fasta'] = [{'filename': fasta,
                              'url': url}]  # set fasta for visualize
            statement = 'MATCH p=(n {name:{filename}})<-[:DERIVED_FROM*1..]-(m) return distinct m'  # should be one line fix later get all files derived from fasta
            return_me = []
            seen = {}
            for r in session.run(statement, {'filename' : fasta}):
                properties = r[0].properties  # get properties of m
                filename = properties['name']
                filetype = properties['filetype']
                assert filename, 'files should have a name this one doesnt' 
                assert filetype, 'files should have a type this one doesnt'
                url = properties['url']
                if not url:  # not an error, but won't return for visual
                    logger.warning('No url for {} will not return'.format(
                                                                     filename))
                    continue
                if filename in seen:  # continue if already seen
                    continue
                seen[filename] = 1
                if filetype not in data:
                    data[filetype] = []
                data[filetype].append({'filename': filename, 'url' : url})
#                return_me.append(r[0].properties)  # get dictionary
            statement = 'MATCH p=(n {name:{filename}})<-[:DERIVED_FROM*1..]-(m)-[:DERIVED_FROM]->(o) return distinct m, o'
            for r in session.run(statement, {'filename' : fasta}):
#                properties_m = r[0].properties  # get properties of m
                properties_o = r[1].properties  # get propteries of o
#                filename_m = properties_m['name']
#                filetype_m = properties_m['filetype']
                filename_o = properties_o['name']
                filetype_o = properties_o['filetype']
#                assert filename, 'files should have a name this one doesnt'
#                assert filetype, 'files should have a type this one doesnt'
                assert filename_o, 'files should have a name this one doesnt'
                assert filetype_o, 'files should have a type this one doesnt'
                if filename_o in seen:  # continue if already seen
                    continue
                seen[filename_o] = 1
                url = properties_o['url']
                if not url:  # not an error, but won't return for visual
                    logger.warning('No url for {} will not return'.format(
                                                                   filename_o))
                    continue
                if filetype_o not in data:
                    data[filetype_o] = []
                data[filetype_o].append({'filename': filename_o, 'url' : url})
        # create template
#        return jsonify(visualize_me), 200
#    response = make_response(render_template_string(app.neo4j_example))
    response = make_response(render_template_string(igv_template.render_igv(visualize_me)))
#    response.headers['Access-Control-Allow-Origin'] =  '*'
#    response = render_template('templating/templates/test_me_linkout.html',
#                               static_path='/static')
    return response


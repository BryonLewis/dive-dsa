const { gitDescribeSync } = require('git-describe');
const path = require('path');
const http = require('http');
const packagejson = require('./package.json');
const SentryPlugin = require('@sentry/webpack-plugin');

const keepAliveAgent = new http.Agent({ keepAlive: true });

process.env.VUE_APP_GIT_HASH = gitDescribeSync().hash;
process.env.VUE_APP_VERSION = packagejson.version;
const staticPath = process.env.NODE_ENV === 'production' ? process.env.VUE_APP_STATIC_PATH || './static/dive' : './';
function chainWebpack(config) {
  config.output.strictModuleExceptionHandling(true);
  config.resolve.symlinks(false);
  config.resolve.alias.set('dive-common', path.resolve(__dirname, 'dive-common'));
  config.resolve.alias.set('vue-media-annotator', path.resolve(__dirname, 'src'));
  config.resolve.alias.set('platform', path.resolve(__dirname, 'platform'));
  // This is needed for local development when using a package json that has "@bryonlewis/mypackage: "file:/home/bryon/dev/package"
  // It will ignore the additional node_modules that are loaded.
  config.resolve.alias.set('vue$', path.resolve(__dirname, './node_modules/vue/dist/vue.runtime.esm.js'));

  config.externals({
    /**
     * Specify vtkjs as external dependency on global context to
     * prevent it from being included in bundle (2MB savings)
     */
    'vtk.js': 'vtkjs',
  });
}

module.exports = {
  devServer: {
    proxy: {
      '/api': {
        target: 'http://localhost:8010',
        secure: false,
        ws: true,
        agent: keepAliveAgent,
      },
    },
  },
  productionSourceMap: true,
  publicPath: staticPath,
  chainWebpack,
  pluginOptions: {
  },
};
